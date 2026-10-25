"""Freeze complete contemporaneous arms and sample before any model answers."""
import copy,csv,json,sys
from collections import Counter,defaultdict
import common093 as c
sys.path.insert(0,str(c.ROOT/'tasks/087_f4_evidence_intervention'))
from common087 import canonical
MODEL='deepseek-v4-flash-0731';CAP=20.
def bound(body):return ((len(canonical(body).encode('utf-8'))+2000)*3+body['max_tokens']*9)/1e6
def main():
    assert c.read(c.OUT/'pool_summary.json')['feasibility_pass']
    source=c.ROOT/'outputs/replays/090_demo_constructor_repair_validation/main_jobs.jsonl'
    with source.open(encoding='utf-8') as f:template=next(j['body'] for j in map(json.loads,f) if j['arm']=='B')
    assert template['model']==MODEL and template['max_tokens']==8192 and template['enable_thinking'] and template['reasoning_effort']=='high'
    pool=c.lines(c.PRIVATE/'pool_inputs.jsonl');ops={r['id']:r for r in c.lines(c.OUT/'pool_operations.jsonl')}
    master={r['proposition_id']:r for r in csv.DictReader((c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig',newline='')) if r['proposition_type']=='claim' and r['invalid']=='False'}
    assert all(r['id'] in master and str(master[r['id']]['subject_id'])==r['sid'] for r in pool)
    # Fixed deterministic sample priority; no historical model predictions consulted.
    ranked=sorted(pool,key=lambda r:(c.h('093/natural/'+r['id']),r['id']))
    pressures={label:sorted([r for r in pool if master[r['id']]['human_gt']==label],key=lambda r:(c.h('093/pressure/patient/'+r['sid']),c.h('093/pressure/'+r['id']))) for label in ['Not Supported','Not Addressed']}
    def mk(r,arm,phase='main'):
        body=copy.deepcopy(template);body['messages'][1]['content']=json.dumps(dict(proposition=r['claim'],reference=r[arm]),ensure_ascii=False,separators=(',',':'))
        rid=c.h('093/'+phase+'/'+r['id']+'/'+c.h(canonical(body)))[:28]
        return dict(request_id=rid,id=r['id'],sid=r['sid'],phase=phase,first_arm=arm,body=body,body_sha256=c.h(canonical(body)),bound_cny=bound(body))
    sample=[];jobs={};aliases=[];selected=set();natural_n=0;pressure_n=0
    for block in range(40):
        trial=[];used=set(selected)
        for r in ranked:
            if r['id'] in used:continue
            trial.append((r,'natural'));used.add(r['id'])
            if len(trial)==3:break
        label=['Not Supported','Not Addressed'][block%2]
        # Patient-round-robin pressure selection, deterministic within GT stratum.
        counts=Counter(r['sid'] for r in sample if r['panel']=='pressure')
        available=[r for r in pressures[label] if r['id'] not in used]
        if len(trial)<3 or not available:break
        pr=min(available,key=lambda r:(counts[r['sid']],c.h('093/pressure/patient/'+r['sid']),c.h('093/pressure/'+r['id'])))
        trial.append((pr,'pressure'));newjobs={};newaliases=[]
        for r,panel in trial:
            for arm in ['B','F','A']:
                job=mk(r,arm);newjobs.setdefault(job['request_id'],job)
                newaliases.append(dict(id=r['id'],panel=panel,arm=arm,request_id=job['request_id'],body_sha256=job['body_sha256']))
        # Entire planned main run remains affordable at byte-bound input and max output.
        if sum(j['bound_cny'] for j in jobs.values())+sum(j['bound_cny'] for j in newjobs.values())>17.8:break
        jobs.update(newjobs);aliases+=newaliases
        for r,panel in trial:
            sample.append(dict(id=r['id'],sid=r['sid'],author=r['author'],panel=panel,GT=master[r['id']]['human_gt'],F_changed=ops[r['id']]['F_changed'],A_added=ops[r['id']]['A_added']))
            selected.add(r['id']);natural_n+=panel=='natural';pressure_n+=panel=='pressure'
    assert natural_n>=24 and pressure_n>=8
    probe=dict(id='synthetic_preflight',sid='synthetic',claim='A synthetic patient had a recorded pulse of 70 beats per minute.',B='Synthetic test record: pulse 70 beats per minute.')
    preflight=mk(probe,'B','preflight');assert preflight['bound_cny']<.2
    # Same-ID arm identities share one first-success response; no repeated successful call.
    main_jobs=sorted(jobs.values(),key=lambda j:c.h('093/dispatch/'+j['request_id']))
    c.putl(c.PRIVATE/'main_jobs.jsonl',main_jobs);c.put(c.PRIVATE/'preflight.json',preflight);c.putl(c.OUT/'sample.jsonl',sample);c.putl(c.OUT/'logical_aliases.jsonl',aliases)
    c.put(c.OUT/'price_policy.json',dict(verified_utc=c.now(),url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',snapshot=MODEL,region='Beijing',input_per_million_cny=3,output_per_million_cny=9,basis='0731 snapshot busy-time undiscounted no-cache ceiling; general unversioned 1/2 price not used',discount_expands_budget=False))
    sources={str(p.relative_to(c.ROOT)).replace('\\','/'):c.sha(p) for p in [c.TASK/'protocol.md',c.TASK/'operation093.py',c.TASK/'build_pool093.py',c.TASK/'prepare093.py',c.OUT/'pool_operations.jsonl',c.PRIVATE/'pool_inputs.jsonl',c.PRIVATE/'main_jobs.jsonl',c.PRIVATE/'preflight.json',c.OUT/'sample.jsonl',c.OUT/'logical_aliases.jsonl']}
    c.put(c.OUT/'main_freeze.json',dict(utc=c.now(),cap_cny=20,main_worst_case_cny=sum(j['bound_cny'] for j in main_jobs),preflight_worst_case_cny=preflight['bound_cny'],recovery_reserve_cny=2.,physical_main_requests=len(main_jobs),logical_main_positions=len(aliases),panels={p:dict(N=sum(r['panel']==p for r in sample),patients=len({r['sid'] for r in sample if r['panel']==p}),GT=dict(Counter(r['GT'] for r in sample if r['panel']==p)),F_changed=sum(r['panel']==p and r['F_changed'] for r in sample),A_changed=sum(r['panel']==p and r['A_added']>0 for r in sample)) for p in ['natural','pressure']},sources=sources,template_source=str(source.relative_to(c.ROOT)).replace('\\','/'),template_sha256=c.h(canonical(template)),model=MODEL,primary='A vs B PriorG, natural panel; F isolates factoring and A vs F isolates additions',invalid_policy='No historical answer fallback: final label only for valid core scores; common-three-arm valid paired metrics, full-N coverage/invalid and conservative correct/N separately. Raw validity evaluated separately. Invalid never silently NA.',GT_in_prompts=False,priorg_refit=False))
    print(c.read(c.OUT/'main_freeze.json')['panels']);print('unique requests',len(main_jobs),'worst main',sum(j['bound_cny'] for j in main_jobs))
if __name__=='__main__':main()
