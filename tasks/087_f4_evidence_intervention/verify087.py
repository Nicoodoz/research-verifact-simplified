"""Executor self-check, entirely offline; output must be a new file."""
import argparse, datetime, subprocess
from collections import Counter
import numpy as np
from sklearn.metrics import matthews_corrcoef,confusion_matrix,f1_score
from common087 import *
import run087 as r
import analyze087 as a

def main(output):
    checks=[]
    def ok(v,name):
        if not v:raise AssertionError(name)
        checks.append(name)
    jobs=r.check_jobs();freeze=read(OUT/'freeze.json');rows,attempts,gtsha=a.collect()
    saved=lines(OUT/'predictions.jsonl');analysis=read(OUT/'analysis.json')
    ok(rows==saved,'native_reparse_all_predictions')
    ok(sha(OUT/'predictions.jsonl')==analysis['predictions_sha256'],'prediction_sha')
    ok(gtsha==analysis['GT_source_sha256'],'GT_source_sha')
    ok(len(rows)==110 and len(jobs)==440,'complete_four_arm_cohort')
    ok(len({x['sid'] for x in rows})==22,'patients_22')
    jobmap={x['request_id']:x for x in jobs}
    for x in attempts:
        req=read(ROOT/x['request_source']);j=req['job']
        ok(j==jobmap[j['request_id']],'request_exact_frozen_job')
        ok(req['created_utc']>=freeze['created_utc'],'request_after_freeze')
        rp=ROOT/x['receipt_source'];rec=read(rp);tr=rec['transport']
        ok(rec['request_sha256']==sha(ROOT/x['request_source']),'request_receipt_binding')
        ok(abs(r.charge(req,tr)-x['cost_or_unknown_cny'])<1e-12,'cost_recomputed')
        if tr['http_status']==200:
            ok(json.loads(tr['body_text'])['model']==MODEL,'returned_exact_model')
            ok(x['cost_or_unknown_cny']<=req['reservation_cny']+1e-12,'within_attempt_reservation')
    counts=Counter(x['request_id'] for x in attempts if x['http_status']==200)
    ok(set(counts)==set(jobmap) and all(v==1 for v in counts.values()),'successful_answer_once_each')
    total=sum(x['cost_or_unknown_cny'] for x in attempts)
    ok(total<=20+1e-9 and abs(total-analysis['cost']['total_original_or_unknown_cny'])<1e-9,'20_cap_and_cost_conservation')
    for subset,table in ((rows,analysis['full_metrics']),([x for x in rows if all(x['arms'][arm]['valid'] for arm in ARMS)],analysis['common_core_metrics'])):
        truth=[x['GT'] for x in subset]
        for m in METHODS:
            for arm in ('Original',)+ARMS:
                pred=[x['labels'][arm][m] for x in subset];metric=table[m][arm]
                ok(abs(matthews_corrcoef(truth,pred)-metric['MCC'])<1e-12,'sklearn_MCC')
                ok(confusion_matrix(truth,pred,labels=LABELS).tolist()==metric['confusion_matrix'],'sklearn_confusion')
                ok(abs(f1_score(truth,pred,labels=LABELS,average='macro',zero_division=0)-metric['Macro_F1'])<1e-12,'sklearn_macroF1')
                ok(sum(b==c for b,c in zip(truth,pred))==metric['correct'],'correct_count')
                ok(sum(g!='Supported' and p=='Supported' for g,p in zip(truth,pred))==metric['false_S'],'false_support')
    for x in rows:
        for arm in ARMS:
            z=x['arms'][arm]
            if not z['valid']:
                ok(z['raw_verdict'] is None and z['scores'] is None,'native_invalid_remains_null')
                ok(all(v==x['fallback_U2'] for v in x['labels'][arm].values()),'shared_frozen_fallback')
            else:
                ok(a.priorg(z['scores'])==x['labels'][arm]['PriorG'],'frozen_priorg')
    cases=lines(OUT/'attribution_cases.jsonl')
    common=[x for x in rows if all(x['arms'][arm]['valid'] for arm in ARMS)]
    for subset,key in ((rows,'full_comparisons'),(common,'common_core_comparisons')):
        for method in METHODS:
            for base,cand in a.PAIRS:
                ok(a.compare(subset,base,cand,method)==analysis[key][method][f'{cand}-{base}'],'shared_patient_bootstrap_replay')
    for base,cand in a.PAIRS:
        key=f'{cand}-{base}';z=[x for x in cases if x['comparison']==key];pair=analysis['full_comparisons']['PriorG'][key]
        ok(len(z)==110,'attribution_full_denominator')
        ok(sum(x['rescue'] for x in z)==pair['rescue'] and sum(x['harm'] for x in z)==pair['harm'],'attribution_conservation')
        for x in z:
            ok(x['both_valid'] or (x['kind']=='invalid_or_fallback_related' and x['raw_rescue'] is None),'invalid_first')
    # Check independent scalar implementation against frozen 086 actual outputs.
    for x in lines(ROOT/'outputs/086_global_demonstration_selection/E_predictions.jsonl'):
        for arm in ('F4_new','N1_new','R1_new'):
            if x['arms'][arm]['valid']:ok(priorg(x['arms'][arm]['scores'])==x['labels'][arm]['PriorG'],'086_frozen_mapping_equivalence')
    corr=read(OUT/'086_correction.json')
    for rel,digest in corr['source_sha256'].items():ok(sha(ROOT/rel)==digest,'086_original_unchanged')
    ok((corr['system_rescue'],corr['system_harm'],corr['valid_rescue'],corr['valid_harm'],corr['fallback_rescue'])==(2,3,1,3,1),'086_correction_counts')
    # Source code/archives guarded by check_jobs; only new 087 files and current navigation may change.
    changed=subprocess.check_output(['git','-c','core.quotepath=false','diff','--name-only',freeze['head']],cwd=ROOT,text=True,encoding='utf-8').splitlines()
    allowed={'.gitattributes','AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/REPRODUCIBILITY.md',
             'docs/087_Codex_F4证据信息干预与紧凑示范验证_执行提示词.md'}
    oldattr=subprocess.check_output(['git','show',freeze['head']+':.gitattributes'],cwd=ROOT)
    newattr=(ROOT/'.gitattributes').read_bytes()
    suffix=newattr[len(oldattr):].decode('utf-8').strip()
    attr_safe=newattr.startswith(oldattr) and suffix=='# Preserve the frozen 087 task instruction bytes.\ndocs/087_* -text'.replace('\n','\r\n')
    attr_safe=attr_safe or (newattr.startswith(oldattr) and suffix=='# Preserve the frozen 087 task instruction bytes.\ndocs/087_* -text')
    ok(attr_safe and all(x in allowed or x.startswith(('tasks/087_f4_evidence_intervention/','outputs/087_f4_evidence_intervention/')) for x in changed),'no_historical_tracked_mutations')
    ok('.gitignore' not in changed,'gitignore_unchanged')
    result=dict(status='PASS',checks=len(checks),check_counts=dict(Counter(checks)),independent_audit=False,
                attempts=len(attempts),original_or_unknown_cny=total,created_utc=now())
    put(output,result);print(canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(OUT/'selfcheck.json'));args=p.parse_args();main(Path(args.output))
