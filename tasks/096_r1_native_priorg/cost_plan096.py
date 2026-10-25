"""Zero-call cost scenarios and optionalV4 exact-input bridge manifests."""
import sys,statistics,json
import common096 as c
sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from cache095 import body_of
def main():
    old=[r for r in c.lines(c.ROOT/'outputs/085_r1_70b_valdemardi/formal_request_ledger.jsonl') if r['arm']=='B'];mean=statistics.mean(r['elapsed_seconds'] for r in old);median=statistics.median(r['elapsed_seconds'] for r in old)
    variants=c.read(c.OUT/'panel_variants.json');plans=[]
    for name,v in variants.items():
        n=143+len(v['main_ids'])+len(v['stress_ids'])+1
        plans.append(dict(name=name,clinical=n-1,synthetic=1,historical_B_serial_hours=n*mean/3600,ideal_two_concurrent_hours=n*mean/7200,planning_two_concurrent_hours_1_5_margin=n*mean/7200*1.5,actual_gpu_hourly_rate=None,actual_gpu_cost=None,formula='(actual loading/wait/preparation hours + measured remaining inference hours + shutdown margin) * user whole-instance hourly rate'))
    base={r['id']:r for r in c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl')};jobs={};bridge_plans={}
    for name,v in variants.items():
        ids=sorted(v['main_ids'],key=lambda pid:c.key('096/v4bridge/v1/',pid))[:48];bridge_plans[name]=ids
        for pid in ids:
            r=base[pid];req=c.read(c.ROOT/r['B']['request_path']);body,_=body_of(req);assert body and body['model']=='deepseek-v4-flash-0731'
            payload=json.loads(body['messages'][1]['content']);assert c.key('',payload['proposition'])==r['claim_sha256'] and c.key('',payload['reference'])==r['reference_sha256']
            h=c.digest(body);bound=((len(c.encoded(body['messages']))+2000)*3+8192*9)/1e6
            jobs[pid]=dict(id=pid,request_id=c.key('096/v4bridge/'+pid+'/',h)[:32],body=body,body_sha256=h,bound_cny=bound)
    c.putl(c.PRIVATE/'v4_bridge_jobs.jsonl',list(jobs.values()));c.putl(c.OUT/'v4_bridge_request_manifest.jsonl',[{k:j[k] for k in ['id','request_id','body_sha256','bound_cny']} for j in jobs.values()]);c.put(c.OUT/'v4_bridge_variants.json',bridge_plans)
    bridge=[]
    for name,ids in bridge_plans.items():
        usages=[base[pid]['B']['parsed']['usage'] for pid in ids];peak=sum((u['prompt_tokens']*3+u['completion_tokens']*9)/1e6 for u in usages)
        bridge.append(dict(plan=name,N=len(ids),historical_usage_busy_no_cache_cny=peak,historical_usage_idle_no_cache_cny=peak*.5,all_requests_maximum_initial_bound_cny=sum(jobs[pid]['bound_cny'] for pid in ids),enabled=False,cap_confirmed=False))
    c.put(c.OUT/'cost_plan.json',dict(status='OFFLINE_ESTIMATES_NOT_BUDGET_AUTHORIZATION',new_R1_calls=0,new_metered_API_calls=0,new_metered_API_cost_cny=0,GPU_cost_cny=None,GPU_billing_start=None,GPU_rate=None,GPU_cap_confirmed=None,metered_cap_confirmed=None,suggested_GPU_cap=30,suggested_metered_cap=10,historical_B_N=len(old),historical_B_mean_seconds=mean,historical_B_median_seconds=median,historical_B_mean_completion_tokens=statistics.mean(r['completion_tokens'] for r in old),R1_scenarios=plans,V4_bridge_scenarios=bridge,warning='Historical085 throughput and ideal concurrency scaling are estimates, not fresh benchmarks or actual GPU rental bill. Current service must be measured before one-time scale choice. No account balance queried;095 budget not inherited.'))
    print('COST_PLAN_OFFLINE',mean,'historic seconds/request; no actual hourly price assumed')
if __name__=='__main__':main()
