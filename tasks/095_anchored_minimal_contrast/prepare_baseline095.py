import copy,statistics
from collections import Counter
import common095 as c
def make_job(pid,phase,arm,body):return dict(request_id=c.h('095/'+phase+'/'+arm+'/'+pid)[:28],id=pid,phase=phase,arm=arm,body=body,body_sha256=c.h(c.canonical(body)),bound_cny=((len(c.canonical(body).encode())+2000)*3+body['max_tokens']*9)/1e6)
def main():
    inp={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};t=c.read(c.PRIVATE/'judge_template.json');missing=c.lines(c.OUT/'baseline_missing_initial.jsonl');jobs=[]
    for r in missing:
        x=inp[r['id']];b=copy.deepcopy(t);b['messages'][1]['content']=c.canonical(dict(proposition=x['text'],reference=x['reference']));jobs.append(make_job(r['id'],'baseline','B',b))
    c.putl(c.PRIVATE/'baseline_jobs.jsonl',jobs)
    selected=c.lines(c.OUT/'cache_selected.jsonl');amounts=[]
    for r in selected:
        u=r['parsed']['usage'];amounts.append((u['prompt_tokens']*3+u['completion_tokens']*9)/1e6)
    mean=statistics.mean(amounts);plan=dict(utc=c.now(),N=9065,cached=len(selected),missing=len(jobs),mean_historical_peak_no_cache=mean,missing_estimated_peak=mean*len(jobs),missing_idle_scenario=mean*len(jobs)/2,baseline_phase_cap_cny=80,method_phase_cap_cny=45,extension_cap_cny=35,routine_task_cap_cny=130,hard_task_cap_cny=150,reserve_cny=20,order='fixed SHA256 095/baseline/ID prefix, continue until next request cannot fit baseline cap; no correctness inspection',initial_workers=8,max_workers=16,prices=dict(region='cn-beijing',model=c.MODEL,busy=dict(input=3,output=9,cached_input=.3),idle=dict(input=1.5,output=4.5,cached_input=.15),source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',time_verification='Official model page confirms rates but does not specify ordinary-service peak windows. Confidential-MaaS 22:00-08:00 definition applies to different model/service and is NOT silently inherited. Current local hour recorded; hard accounting uses confirmed busy ceiling, idle is scenario until ordinary-service interval is independently confirmed.',cache='Only actual usage.prompt_tokens_details.cached_tokens; missing field=0; no hit assumed'),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.TASK/'protocol.md',c.TASK/'prepare_baseline095.py',c.PRIVATE/'baseline_jobs.jsonl',c.OUT/'cache_selected.jsonl',c.OUT/'reference_inventory.jsonl']})
    c.put(c.OUT/'baseline_plan.json',plan);c.progress('A_plan',f'1885 cached; {len(jobs)} missing; peak estimate {mean*len(jobs):.2f}; cap 80 leaves method budget.');print('missing',len(jobs),'peak estimate',mean*len(jobs),'idle scenario',mean*len(jobs)/2)
if __name__=='__main__':main()
