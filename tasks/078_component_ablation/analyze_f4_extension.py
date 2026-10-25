"""Score fixed F4 completion on same-ID cohorts; preserve all initial078 results."""
import copy
from collections import Counter
from threadpoolctl import threadpool_limits
import analyze078 as a
import run_f4_extension as r
c=r.c
OLD=c.ROOT/'outputs/078_component_ablation'
METHODS=['Original','NS_U2','GateA','NS_StdM','NS_StdV','NS_prior','TS_raw','F4_raw','TS_U2','F4_U2','TS_PriorG','F4_PriorG']
PAIRS=[('TS_raw','F4_raw'),('TS_U2','F4_U2'),('TS_PriorG','F4_PriorG'),('Original','F4_PriorG')]

def main():
    r.verify()
    attempts,answers=r.state()
    jobs=c.lines(c.OUT/'main_jobs.jsonl')
    assert set(answers)=={j['request_id'] for j in jobs} and len(answers)==256
    original=c.lines(OLD/'predictions.jsonl')
    rows=copy.deepcopy(original)
    by={x['job']['id']:x for x in answers.values()}
    freeze=c.read(OLD/'postprocessing_frozen.json')
    theta=freeze['calibration_theta']['T-S']['G']
    ref=freeze['reference_prior_counts'];cc=freeze['calibration_counts']['T-S']
    invalid=[]
    for x in rows:
        if x['id'] not in by:
            assert 'F4' in x['arms']
            continue
        assert 'F4' not in x['arms']
        z=by[x['id']];j=z['job'];p=z['parsed']
        ts=c.read(c.ROOT/x['arms']['TS']['request_source'])['job']['body']
        assert j['body']['messages'][1:]==ts['messages'][1:]
        valid=p['status'] in c.c53.VALID and p.get('scores') is not None
        fallback=x['methods']['NS_U2']['label']
        cost=c.charge(z['transport'],c.bound(j['body']))+(0 if valid else x['methods']['NS_U2']['judge_cost_cny'])
        x['arms']['F4']=dict(arm='F4',status=p['status'],valid=valid,raw=p.get('verdict'),scores=p.get('scores'),usage=p.get('usage'),mode='extension_new',body_sha256=j['body_sha256'],request_source=z['request_source'],receipt_source=z['receipt_source'])
        if not valid:invalid.append(dict(id=x['id'],sid=x['sid'],status=p['status'],errors=p.get('errors'),fallback=fallback))
        for post in ['raw','U0','U2','G','prior','PriorG']:
            label=fallback
            if valid:
                if post=='raw':label=p['verdict']
                elif post in ['U0','U2']:label=c.c53.decision(p['scores'],0 if post=='U0' else 2)
                else:
                    logs=c.c53.calibrated(p['scores'],theta,'G') if post in ['G','PriorG'] else c.c53.log_scores(p['scores'])
                    if post in ['prior','PriorG']:logs=c.c53.prior_adjust(logs,ref,cc)
                    label=c.c53.decode_logits(logs)
            x['methods']['F4_'+post]=dict(label=label,valid=valid,fallback=not valid,judge_cost_cny=cost,arm='F4')
    # Preserve every baseline and all128 existing F4 predictions exactly.
    for old,new in zip(original,rows):
        for k,v in old['methods'].items():assert new['methods'][k]==v
        for k,v in old['arms'].items():assert new['arms'][k]==v
    plan=c.read(c.OUT/'proposed_plan.json')
    cohorts=dict(plan['cohorts'])
    cohorts['new224_no_example_patient']=[x['id'] for x in rows if x['id'] in by and x['sid'] not in plan['example_patients']]
    assert len(cohorts['new224_no_example_patient'])==224
    tables={};pairs={};lists={}
    for name,ids in cohorts.items():
        rr=[x for x in rows if x['id'] in set(ids)]
        tables[name]=a.table(rr,METHODS);lists[name]=ids
        if len(rr)>=32:pairs[name]=[a.pair(rr,b,f) for b,f in PAIRS]
        if name in ['all384_descriptive','exclude_actual_example_patients352','original_pool_isolated128']:
            for suffix,sub in [('human',[x for x in rr if x['author']=='human']),('llm',[x for x in rr if x['author']=='llm']),('common_core',[x for x in rr if all(x['methods'][m]['valid'] for m in METHODS)])]:
                key=name+'_'+suffix;tables[key]=a.table(sub,METHODS);lists[key]=[x['id'] for x in sub]
                pairs[key]=[a.pair(sub,b,f) for b,f in PAIRS[:3]]
        print(c.canon(dict(cohort=name,n=len(rr),status='scored')),flush=True)
    prior=c.read(OLD/'tables.json')['F4_all']
    current={m['method']:m for m in tables['original_pool_isolated128']}
    for m in prior:
        if m['method'] in current:
            for key in ['MCC','PA','correct','falseS','fallback']:assert m[key]==current[m['method']][key]
    c.jl(c.OUT/'predictions.jsonl',rows)
    c.put(c.OUT/'tables.json',tables);c.put(c.OUT/'paired_comparisons.json',pairs);c.put(c.OUT/'cohort_lists.json',lists)
    c.put(c.OUT/'invalid_outputs.json',invalid)
    newcost=sum(x['cost_cny'] for x in attempts)
    oldcost=c.read(c.OUT/'authorization.json')['old_spent_cny']
    total=oldcost+newcost;assert total<=35
    c.put(c.OUT/'cost_ledger.json',dict(prior078_cny=oldcost,extension_cny=newcost,total078_cny=total,cap_cny=35,
        new_logical=256,new_attempts=len(attempts),http_counts=dict(Counter(str(x['http_status']) for x in attempts)),
        unknown_reserved_cny=sum(x['cost_cny'] for x in attempts if x['http_status'] in [0,None]),attempts=attempts,
        pricing='0731 Beijing busy list3/9 CNY per million; estimated usage cost, not billing reconciliation'))
    sourcechecks=0
    for path,h in c.read(OLD/'manifest.json')['files'].items():
        assert c.sha(c.ROOT/path)==h,path
        sourcechecks+=1
    c.put(c.OUT/'verification.json',dict(status='PASS',all256_HTTP200=True,new_core_valid=256-len(invalid),new_core_invalid=len(invalid),
        old_manifest_files_unchanged=sourcechecks,old128_metrics_unchanged=True,all_baselines_unchanged=True,
        exact_demo_overlap=2,same_demo_patient_rows=32,actual_demo_patient_excluded=352,new_non_demo_patient_rows=224,
        new_fits=0,independent_audit='not performed',analysis_sha256=c.sha(c.TASK/'analyze_f4_extension.py')))
    print(c.canon(dict(status='PASS',newcost=newcost,total=total,invalid=len(invalid))))

if __name__=='__main__':
    with threadpool_limits(limits=1):main()
