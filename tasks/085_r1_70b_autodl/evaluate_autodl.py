"""Deferred GT-blind materialization and085A shared four-arm evaluation; never impute R1."""
import argparse
from common import *
import runner
sys.path.insert(0,str(ROOT/'tasks/085_r1_70b_model_swap'))
import evaluate085 as ev
from parse_r1 import ParserProfile,parse
def materialize():
    jobs=runner.load_jobs();pf=OUT/'preflight/parser_profile.json';profile=ParserProfile.from_json(read(pf));_,success,_=runner.state();rows=[]
    for j in jobs:
        s=success.get(j['request_id'])
        base=dict(id=j['id'],sid=j['sid'],arm=j['arm'],request_id=j['request_id'],body_sha256=j['body_sha256'],parser_profile_sha256=sha(pf))
        if not s:
            rows.append(dict(base,valid=False,invalid_reason='missing_successful_response',verdict=None,label_scores=None,raw_response_path=None,raw_response_sha256=None));continue
        raw=ROOT/s['folder']/'response.raw';parsed=parse(raw.read_bytes(),profile)
        try:envelope=json.loads(raw.read_bytes());model_ok=envelope.get('model')==MODEL
        except (ValueError,AttributeError):model_ok=False
        if not model_ok:parsed.update(valid=False,invalid_reason='invalid_or_missing_model_envelope',verdict=None,label_scores=None)
        rows.append(dict(base,raw_response_path=raw.relative_to(ROOT).as_posix(),raw_response_sha256=sha(raw),**parsed))
    putl(OUT/'r1_predictions.jsonl',rows);return rows
def evaluate(allow_incomplete=False):
    check_old();rows=lines(OUT/'r1_predictions.jsonl');assert len(rows)==360
    pairs={(x['id'],x['arm']):x for x in rows};assert len(pairs)==360
    missing=[x for x in rows if not x.get('raw_response_path')]
    if missing and not allow_incomplete:raise RuntimeError('Formal evaluation incomplete; missing slots retained, no old-answer filling')
    old={x['id']:x for x in lines(ROOT/'outputs/084_f4_coverage_validation/new_predictions.jsonl')}
    manifest=lines(OLD/'frozen_cohort_manifest.jsonl');common=[];invalid=[];secondary=[]
    pf=OUT/'preflight/parser_profile.json'
    for x in rows:
        assert x['parser_profile_sha256']==sha(pf)
        if x.get('raw_response_path'):assert sha(ROOT/x['raw_response_path'])==x['raw_response_sha256']
    for m in manifest:
        pid=m['id'];b=pairs[pid,'B'];f=pairs[pid,'F4'];v=old[pid]
        assert b['sid']==f['sid']==m['sid']
        valid=b['valid'] and f['valid'] and v['arms']['B']['valid'] and v['arms']['F4']['valid']
        if not valid:
            invalid.append(dict(id=pid,sid=m['sid'],R1_B=b.get('invalid_reason'),R1_F4=f.get('invalid_reason'),V4_B_valid=v['arms']['B']['valid'],V4_F4_valid=v['arms']['F4']['valid']));continue
        row=dict(id=pid,sid=m['sid'],GT=v['GT'],labels={'V4-B':v['arms']['B']['raw'],'V4-F4':v['arms']['F4']['raw'],'R1-B':b['verdict'],'R1-F4':f['verdict']});common.append(row)
        if b.get('label_scores') and f.get('label_scores'):
            secondary.append(dict(id=pid,sid=m['sid'],GT=v['GT'],labels={f'R1-{a}-{method}':fn(s) for a,s in (('B',b['label_scores']),('F4',f['label_scores'])) for method,fn in (
                ('U0',lambda s:ev.decision(s,0)),('U2',lambda s:ev.decision(s,2)),('FrozenPriorG',ev.priorg))}))
    result=dict(status='FORMAL_COMPLETE' if not missing else 'INCOMPLETE_DIAGNOSTIC',frozen_n=180,common_valid_n=len(common),invalid_or_missing=invalid,
        per_arm_coverage={a:dict(total=180,valid=sum(x['arm']==a and x['valid'] for x in rows),missing=sum(x['arm']==a for x in missing)) for a in ('B','F4')},
        primary={a:ev.summary(common,a) for a in ev.ARMS} if common else {},comparisons={f'{c} minus {b}':ev.compare(common,b,c) for b,c in (('V4-B','R1-B'),('R1-B','R1-F4'),('V4-F4','R1-F4'),('V4-B','V4-F4'))} if common else {},
        F4_cross_model_effect=ev.effect_difference(common) if common else None,secondary_score_valid_n=len(secondary),
        secondary_compatibility={a:ev.summary(secondary,a) for a in secondary[0]['labels']} if secondary else {},
        identity='Pinned same AWQ repository/checkpoint target, current frozen prompt controlled model swap; NOT original full VeriFact Judge pipeline byte reproduction',
        no_R1_imputation=True,no_new_fit=True,GT_used_before_parsing=False)
    putl(OUT/'common_valid_primary.jsonl',common);put(OUT/'evaluation.json',result)
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('materialize','evaluate'));p.add_argument('--allow-evaluation',action='store_true');p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args()
    if a.action=='materialize':materialize()
    elif not a.allow_evaluation:raise PermissionError('Evaluation explicitly gated after predictions are frozen')
    else:evaluate(a.allow_incomplete)
if __name__=='__main__':main()
