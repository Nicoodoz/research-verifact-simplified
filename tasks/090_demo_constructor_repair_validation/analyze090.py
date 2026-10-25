"""Fixed two-panel evaluation; raw and score validity retained independently."""
import statistics
from collections import Counter
from common090 import *
import api090 as api
sys.path.insert(0,str(ROOT/'tasks/087_f4_evidence_intervention'))
import analyze087 as shared
from analyze087 import parse_response,decision,VALID,load_gt,metric,compare,dist
sys.path.insert(0,str(ROOT/'tasks/024_lambda2_transfer_validation'))
import core024 as core
PAIRS=(('F4','P90'),('Q90','P90'),('B','F4'),('B','P90'),('B','Q90'),('F4','Q90'))

def native_fields(content):
    raw=None;scores=None;errors=[]
    try:
        try:o=core.loads(content)
        except (ValueError,TypeError):o=core.partial_object(content)
        if not isinstance(o,core.Object):raise ValueError('not object')
        try:
            raw=core.unique(o,'verdict')
            if raw not in LABELS:raw=None
        except (ValueError,TypeError):errors.append('native_verdict_invalid')
        try:
            s=core.unique(o,'label_scores')
            if isinstance(s,dict) and set(s)==set(LABELS) and all(type(v)is int and 0<=v<=100 for v in s.values()) and sum(s.values())==100:scores=s
            else:errors.append('native_scores_invalid')
        except (ValueError,TypeError):errors.append('native_scores_invalid')
    except (ValueError,TypeError,IndexError):errors.append('native_json_invalid')
    return raw,scores,errors
def parse_arm(tr,fallback):
    p=parse_response(tr,True,True);native=json.loads(tr['body_text']);choice=native['choices'][0];msg=choice['message']
    raw,scores,errors=native_fields(msg.get('content'));valid=p['status'] in VALID and p.get('scores') is not None
    assert native.get('model')==MODEL
    if valid:assert raw==p['verdict'] and scores==p['scores']
    labels=dict(raw=raw if raw else fallback,U0=decision(scores,0) if valid else fallback,U2=decision(scores,2) if valid else fallback,PriorG=priorg(scores) if valid else fallback)
    return dict(valid=valid,raw_valid=raw is not None,scores_valid=scores is not None,raw_verdict=raw,scores=scores,status=p['status'],parser_errors=p.get('errors'),native_errors=errors,
        finish_reason=choice.get('finish_reason'),usage=native['usage'],fallback_used=not valid,raw_fallback_used=raw is None,elapsed_seconds=tr.get('client_elapsed_seconds')),labels
def main():
    global ARMS,PAIRS
    ARMS=tuple(read(OUT/'final/templates.json')['active_arms']);PAIRS=tuple((b,c) for b,c in PAIRS if b in ARMS and c in ARMS)
    jobs=api.validate_main();attempts,success,_=api.state();assert all(j['request_id'] in success for j in jobs)
    sample=lines(OUT/'sample_blind.jsonl');gt,original,gtsha=load_gt({x['id'] for x in sample})
    rows={x['id']:{**x,'GT':gt[x['id']]['human_gt'],'arms':{},'labels':{'Original':{m:original[x['id']] for m in METHODS}}} for x in sample}
    for alias in lines(OUT/'logical_aliases.jsonl'):
        x=rows[alias['id']];s=success[alias['request_id']];p=ROOT/s['receipt_source'];tr=read(p)['transport'];info,labels=parse_arm(tr,x['fallback_U2'])
        info.update(receipt_source=s['receipt_source'],receipt_sha256=sha(p),request_source=s['request_source'],request_id=alias['request_id'],body_sha256=alias['body_sha256'])
        x['arms'][alias['arm']]=info;x['labels'][alias['arm']]=labels
    rows=list(rows.values());putl(OUT/'predictions.jsonl',rows)
    panels={};ats=[]
    for panel in ('natural','pressure'):
        z=[x for x in rows if x['panel']==panel];common=[x for x in z if all(x['arms'][a]['valid'] for a in ARMS)]
        raw=[x for x in z if all(x['arms'][a]['raw_valid'] for a in ARMS)]
        d=dict(n=len(z),patients=len({x['sid'] for x in z}),GT=dict(Counter(x['GT'] for x in z)),common_core_n=len(common),raw_common_n=len(raw),
            common_core_excluded=[x['id'] for x in z if x not in common],raw_common_excluded=[x['id'] for x in z if x not in raw],
            full_metrics={m:{a:metric(z,a,m) for a in ('Original',)+ARMS} for m in METHODS},
            common_core_metrics={m:{a:metric(common,a,m) for a in ('Original',)+ARMS} for m in METHODS} if common else {},
            native_raw_metrics={a:metric(raw,a,'raw') for a in ('Original',)+ARMS} if raw else {},
            full_comparisons={m:{f'{c}-{b}':compare(z,b,c,m) for b,c in PAIRS} for m in METHODS},
            common_core_comparisons={m:{f'{c}-{b}':compare(common,b,c,m) for b,c in PAIRS} for m in METHODS} if common else {},
            native_raw_comparisons={f'{c}-{b}':compare(raw,b,c,'raw') for b,c in PAIRS} if raw else {},strata={})
        # Correct inherited informational flag: full raw uses its own validity rather than core validity.
        for a in ARMS:d['full_metrics']['raw'][a]['raw_includes_fallback']=any(x['arms'][a]['raw_fallback_used'] for x in z)
        for field in ('author','selection_tier','teaching_candidate_patient_overlap'):
            for value in sorted({x[field] for x in z},key=str):
                sub=[x for x in z if x[field]==value];d['strata'][f'{field}={value}']=dict(n=len(sub),GT=dict(Counter(x['GT'] for x in sub)),metrics={a:metric(sub,a,'PriorG',False) for a in ARMS})
        for b,c in PAIRS:
            for x in z:
                result=attribution({**x['arms'][b],'final':x['labels'][b]['PriorG']},{**x['arms'][c],'final':x['labels'][c]['PriorG']},x['GT'])
                ats.append(dict(id=x['id'],sid=x['sid'],panel=panel,GT=x['GT'],comparison=f'{c}-{b}',**result))
        d['attribution_summary']={f'{c}-{b}':dict(Counter(v['kind'] for v in ats if v['panel']==panel and v['comparison']==f'{c}-{b}' and (v['rescue'] or v['harm']))) for b,c in PAIRS}
        panels[panel]=d
    ledger=[]
    for a in attempts:
        x=dict(a)
        if a['receipt_source']:
            tr=read(ROOT/a['receipt_source'])['transport']
            if tr.get('http_status')==200:x['usage']=json.loads(tr['body_text']).get('usage')
        ledger.append(x)
    construction=sum(x['cost_or_unknown_cny'] for x in attempts if x['phase']!='main')
    costs=dict(cap=40,total_original_or_unknown_cny=sum(x['cost_or_unknown_cny'] for x in attempts),construction_review_coverage_cny=construction,
        attempts=len(attempts),http_status=dict(Counter(str(x['http_status']) for x in attempts)),unknown_reserve=sum(x['cost_or_unknown_cny'] for x in attempts if x['http_status'] in (None,0)),
        phase_costs={p:sum(x['cost_or_unknown_cny'] for x in attempts if x['phase']==p) for p in sorted({x['phase'] for x in attempts})},arms={})
    for arm in ARMS:
        infos=[x['arms'][arm] for x in rows];us=[x['usage'] for x in infos]
        costs['arms'][arm]=dict(n=len(us),prompt_tokens=sum(u['prompt_tokens'] for u in us),completion_tokens=sum(u['completion_tokens'] for u in us),total_tokens=sum(u['total_tokens'] for u in us),
            logical_success_original_cny=sum((u['prompt_tokens']*3+u['completion_tokens']*9)/1e6 for u in us),prompt_distribution=dist([u['prompt_tokens'] for u in us]),
            completion_distribution=dist([u['completion_tokens'] for u in us]),elapsed_seconds_distribution=dist([x['elapsed_seconds'] for x in infos]),
            core_invalid=sum(not x['valid'] for x in infos),raw_invalid=sum(not x['raw_valid'] for x in infos),scores_invalid=sum(not x['scores_valid'] for x in infos),
            physical_charged_cny=sum(x['cost_or_unknown_cny'] for x in attempts if x['phase']=='main' and x['arm']==arm))
    costs['shared_calls_note']='Logical arm costs describe deployment. Sum physical attempts only for task cost; identical bodies shared.'
    costs['amortized_construction_per_case']={str(n):construction/n for n in (100,1000,10000)}
    assert costs['total_original_or_unknown_cny']<=40 and construction<=4
    putl(OUT/'attempt_ledger.jsonl',ledger);put(OUT/'cost_ledger.json',costs);putl(OUT/'attribution_cases.jsonl',ats)
    put(OUT/'analysis.json',dict(panels=panels,GT_source_sha256=gtsha,cost=costs,primary='natural/P90-F4/PriorG/MCC (only if P90 usable)',
        multiplicity='Fixed contrasts all reported, exploratory 95% intervals without multiplicity correction; zero crossing is not equivalence',
        raw_rule='Native raw independently parsed; full raw table uses032fallback only if raw missing. Native common-valid table has no fallback.'))
    print(canonical(dict(panels={p:{a:(z['full_metrics']['PriorG'][a]['correct'],z['full_metrics']['PriorG'][a]['MCC'],z['full_metrics']['PriorG'][a]['false_S']) for a in ARMS} for p,z in panels.items()},cost=costs['total_original_or_unknown_cny'])))
if __name__=='__main__':main()
