"""Task expenditure vs single-arm deployment cost; no prepaid-credit discounts."""
import json,statistics
from collections import Counter
import common095 as c
import state095 as s
from pricing095 import inside_one_idle_window

def usage_cost(u,idle=False,cache=True):
    cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0) if cache else 0
    return ((u['prompt_tokens']-cached)*3+cached*.3+u['completion_tokens']*9)/1e6*(.5 if idle else 1)

def known_usage(tr,bound):
    if not tr or tr.get('http_status')!=200 or tr.get('outcome_unknown') is True:return False
    try:
        n=json.loads(tr['body_text']);u=n['usage'];i=u['prompt_tokens'];o=u['completion_tokens'];h=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        return n.get('model')==c.MODEL and all(type(v)is int and v>=0 for v in [i,o,h]) and h<=i and usage_cost(u)<=bound+1e-8
    except (KeyError,ValueError,TypeError):return False

def main():
    assert not (c.PRIVATE/'run.lock').exists()
    aa=s.attempts();success=s.successful_jobs();charges=Counter();unknown=0;hour=Counter();stages={}
    for a in aa:
        charges[a['phase']]+=a['charge_or_reserved_cny'];hour[a['utc'][:13]]+=1
        tr=c.read(c.ROOT/a['receipt_path'])['transport'] if a['receipt_path'] else None
        bound=c.read(c.ROOT/a['request_path'])['job']['bound_cny'];a['billing_usage_known']=known_usage(tr,bound)
        if a['billing_usage_known']:a['time_tariff']='idle' if inside_one_idle_window(tr) else 'busy_or_unverified'
        else:
            a['time_tariff']='peak_maximum_unknown';unknown+=a['charge_or_reserved_cny']
    c.putl(c.OUT/'attempt_ledger.jsonl',aa)
    for phase in charges:
        rows=[a for a in aa if a['phase']==phase];us=[r['usage'] for r in rows if r['usage'] and r['billing_usage_known']]
        stages[phase]=dict(attempts=len(rows),HTTP200=sum(r['http_status']==200 for r in rows),charge_or_reserved_cny=charges[phase],input_tokens=sum(u['prompt_tokens'] for u in us),output_tokens=sum(u['completion_tokens'] for u in us),cached_input_tokens=sum(u.get('prompt_tokens_details',{}).get('cached_tokens',0) for u in us),tariffs=dict(Counter(r['time_tariff'] for r in rows)))
    logical={}
    for tag in ['screen','extension']:
        pp=c.OUT/(tag+'_predictions.jsonl')
        if not pp.exists():continue
        rows=c.lines(pp);aud={r['id']:r for r in c.lines(c.OUT/('construction_audit.jsonl' if tag=='screen' else tag+'_construction_audit.jsonl'))};logical[tag]={}
        for panel in ['natural','mechanism']:
            rr=[r for r in rows if r['panel']==panel];logical[tag][panel]={}
            for arm in ['B','E','C']:
                total=Counter();wall=0.;cached_cost=idle_no_cache=busy_no_cache=0.;calls=0;final_calls=0
                for r in rr:
                    ids=[r['arms'][arm]['request_id']];final_calls+=1
                    if arm!='B':
                        q=aud[r['id']];ids.append(q['constructor_request_id'])
                        if q['check_request_id']:ids.append(q['check_request_id'])
                    for rid in ids:
                        tr=s.receipt(success[rid]);u=json.loads(tr['body_text'])['usage'];total['input']+=u['prompt_tokens'];total['output']+=u['completion_tokens'];total['cached_input']+=u.get('prompt_tokens_details',{}).get('cached_tokens',0);wall+=tr['client_elapsed_seconds'];cached_cost+=usage_cost(u,inside_one_idle_window(tr),True);idle_no_cache+=usage_cost(u,True,False);busy_no_cache+=usage_cost(u,False,False);calls+=1
                logical[tag][panel][arm]=dict(N=len(rr),logical_calls=calls,final_Judge_calls=final_calls,extra_auxiliary_calls=calls-final_calls,input_tokens=total['input'],output_tokens=total['output'],cached_input_tokens=total['cached_input'],observed_usage_tariff_cny=cached_cost,idle_no_cache_cny=idle_no_cache,busy_no_cache_cny=busy_no_cache,mean_sequential_seconds=wall/len(rr),note='Each deployed arm includes its constructor/checker even on B fallback. Research E/C share construction physically; logical costs are counterfactual separate deployments, not added to task expenditure. Historical reusable B tariff is current-usage estimate, not new cost.')
    full=[r['B']['parsed']['usage'] for r in c.lines(c.OUT/'unified_9065_predictions.jsonl') if r['B_present']]
    valid=[u for u in full if u and all(type(u.get(k)) is int and u[k]>=0 for k in ['prompt_tokens','completion_tokens'])]
    usage_summary=dict(successful_B=len(full),valid_usage=len(valid),note='Includes reused historical B: token usage only, not all new095 spending. No claim of matching original pipeline hardware cost.')
    for key in ['prompt_tokens','completion_tokens']:
        vals=sorted(u[key] for u in valid)
        usage_summary[key]=dict(total=sum(vals),mean=statistics.mean(vals),median=statistics.median(vals),p95=statistics.quantiles(vals,n=100,method='inclusive')[94],min=min(vals),max=max(vals)) if vals else None
    usage_summary['completion_at_8192']=sum(u['completion_tokens']==8192 for u in valid)
    budget=dict(utc=c.now(),hard_cap_cny=150,normal_planning_cap_cny=130,total_directory_price_or_unknown_cny=sum(charges.values()),remaining_to_hard_cap=150-sum(charges.values()),unknown_reserve_cny=unknown,attempts=len(aa),HTTP200=sum(a['http_status']==200 for a in aa),unique_success=len(success),retry_attempts=sum(a['attempt']>1 for a in aa),phase_costs=dict(charges),stages=stages,UTC_hour_counts=dict(hour),logical_deployment=logical,baseline_full_coverage_usage=usage_summary,price_sources=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://www.alibabacloud.com/en/notice/model_studiodeepseekv4flash0731_price_increase_notice_831?_p_lc=1'],unit='CNY, directory tariffs; real usage cache only, no coupon/prepaid discount',actual_account_invoice_available=False,GPU_rental_new=0,retrieval_new_API=0)
    assert budget['total_directory_price_or_unknown_cny']<=150+1e-8;c.put(c.OUT/'cost_ledger.json',budget);print('Total',budget['total_directory_price_or_unknown_cny'],'stages',dict(charges))
if __name__=='__main__':main()
