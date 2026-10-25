"""Apply frozen two-model calibration to fixed352, then score through public APIs."""
import sys,copy
from collections import Counter
from threadpoolctl import threadpool_limits
import common079 as c
import run079
sys.path.insert(0,str(c.ROOT/'tasks/078_component_ablation'))
import analyze078 as a

NAMES={
 'TS_newG':'B＋新G','TS_newprior':'B＋新校准分布仅先验','TS_newPriorG':'B＋适配PriorG',
 'F4_newG':'F4＋新G','F4_newprior':'F4＋新校准分布仅先验','F4_newPriorG':'F4＋适配PriorG'}
METHODS=['Original','NS_U2','GateA','NS_StdM','NS_StdV','TS_raw','TS_U2','TS_prior','TS_PriorG','TS_newG','TS_newprior','TS_newPriorG',
         'F4_raw','F4_U2','F4_prior','F4_PriorG','F4_newG','F4_newprior','F4_newPriorG']
PAIRS=[('F4_PriorG','F4_newPriorG'),('TS_newPriorG','F4_newPriorG'),('TS_PriorG','F4_newPriorG'),('TS_PriorG','TS_newPriorG'),
       ('F4_newprior','F4_newPriorG'),('TS_newprior','TS_newPriorG'),('F4_prior','F4_newprior'),('TS_prior','TS_newprior'),
       ('Original','TS_PriorG'),('Original','TS_newPriorG'),('Original','F4_PriorG'),('Original','F4_newPriorG')]

def table(rows):
    result=[]
    for method in METHODS:
        m=a.metrics(rows,method);e=a.evaluate(a.cohort(rows),a.prediction(rows,method),profile='none',missing='error')
        m['per_class']=e['per_class'];m['macro_F1']=sum(e['per_class'][k]['f1'] or 0 for k in a.LABELS)/3
        m['balanced_accuracy']=sum(e['per_class'][k]['recall'] or 0 for k in a.LABELS)/3
        result.append(m)
    return result

def main():
    run079.verify();model=c.read(c.OUT/'fitted_models.json')
    assert model['status']=='FROZEN_BEFORE_079_EVALUATION'
    assert c.sha(c.TASK/'fit079.py')==model['fit_code_sha256']
    assert c.sha(c.OUT/'calibration_predictions.jsonl')==model['calibration_predictions_sha256']
    a.NAMES.update(NAMES)
    ext=c.ROOT/'outputs/078_component_ablation/f4_extension_001'
    ids={x['id'] for x in c.lines(c.OUT/'evaluation_blind.jsonl')}
    rows=[copy.deepcopy(x) for x in c.lines(ext/'predictions.jsonl') if x['id'] in ids]
    assert len(rows)==352 and not {x['sid'] for x in rows}&set(model['common_patients'])
    counts=model['calibration_counts'];ref=model['reference_prior_counts']
    for x in rows:
        for arm,fitarm in [('TS','B'),('F4','F4')]:
            meta=x['arms'][arm];theta=model['models'][fitarm]['fit']['theta'];base=x['methods'][arm+'_raw']
            for post in ['newG','newprior','newPriorG']:
                label=x['methods']['NS_U2']['label']
                if meta['valid']:
                    logs=c.c53.calibrated(meta['scores'],theta,'G') if post!='newprior' else c.c53.log_scores(meta['scores'])
                    if post!='newG':logs=c.c53.prior_adjust(logs,ref,counts)
                    label=c.c53.decode_logits(logs)
                x['methods'][arm+'_'+post]=dict(label=label,valid=base['valid'],fallback=base['fallback'],judge_cost_cny=base['judge_cost_cny'],arm=arm)
    # The target labels were already exposed historically; no fit reads them.
    c.put(c.OUT/'evaluation_apply_freeze.json',dict(created_utc=c.now(),model_sha256=c.sha(c.OUT/'fitted_models.json'),
        analysis_sha256=c.sha(c.TASK/'analyze079.py'),evaluation_source_sha256=c.sha(ext/'predictions.jsonl'),n=352,parameter_search_on_evaluation=False))
    c.jl(c.OUT/'predictions.jsonl',rows)
    old128=set(c.read(ext/'cohort_lists.json')['original_pool_isolated128'])
    groups={'all352':rows,'common_core340':[x for x in rows if x['arms']['TS']['valid'] and x['arms']['F4']['valid']],
            'human':[x for x in rows if x['author']=='human'],'llm':[x for x in rows if x['author']=='llm'],'original_pool_isolated128':[x for x in rows if x['id'] in old128]}
    assert len(groups['common_core340'])==340 and len(groups['original_pool_isolated128'])==128
    tables={};pairs={};equivalent={}
    for name,rr in groups.items():
        tables[name]=table(rr);pairs[name]=[a.pair(rr,b,f) for b,f in (PAIRS if name=='all352' else PAIRS[:4])]
        equivalent[name]=[{k:z[k] for k in ['base','candidate','n','rescue','harm','net','delta_falseS']}|{'label_changes':sum(x['methods'][z['base']]['label']!=x['methods'][z['candidate']]['label'] for x in rr)} for z in pairs[name]]
        print(c.canon(dict(cohort=name,n=len(rr),status='scored')),flush=True)
    c.put(c.OUT/'tables.json',tables);c.put(c.OUT/'paired_comparisons.json',pairs);c.put(c.OUT/'changes.json',equivalent)
    # All previously displayed352 metrics must be reproduced exactly.
    old={m['method']:m for m in c.read(ext/'full_table_352/results.json')['rows']}
    for m in tables['all352']:
        if m['method'] in old:
            for k in ['MCC','PA','AC1','correct','falseS','fallback']:assert m[k]==old[m['method']][k]
    attempts,new=run079.state();expense=sum(x['cost_cny'] for x in attempts);assert expense<=20
    c.put(c.OUT/'cost_ledger.json',dict(cap_cny=20,new_api_attempts=len(attempts),new_logical=len(new),reused_F4=len(c.lines(c.OUT/'reused_F4.jsonl')),
        estimated_cny=expense,http_counts=dict(Counter(str(x['http_status']) for x in attempts)),
        unknown_reserved_cny=sum(x['cost_cny'] for x in attempts if x['http_status'] in [0,None]),attempts=attempts))
    before=c.read(c.OUT/'freeze.json');assert c.sha(c.ROOT/'.gitignore')==before['gitignore_sha256']
    c.put(c.OUT/'verification.json',dict(status='PASS',train_eval_patient_overlap=0,old352_metrics_exact=True,new_fits=2,
        calibration_common_n=model['common_n'],new_core_valid=sum(x['parsed']['status'] in c.c53.VALID for x in new.values()),
        new_api_attempts=len(attempts),expense_cny=expense,analysis_sha256=c.sha(c.TASK/'analyze079.py'),
        gitignore_unchanged=True,reserved_used=False,independent_audit='not performed'))
    print(c.canon(dict(status='PASS',expense=expense,changes=equivalent['all352'])),flush=True)

if __name__=='__main__':
    with threadpool_limits(limits=1):main()
