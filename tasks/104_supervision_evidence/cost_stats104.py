"""Offline receipt accounting; no credentials or network use."""
from collections import Counter
import json
import statistics
import common104 as c


def main():
    records=[]
    for request_path in (c.PRIVATE/'api_attempts').glob('*/request.json'):
        request=c.read(request_path);job=request['job'];folder=request_path.parent
        account=c.read(folder/'accounting.json');receipt=c.read(folder/'receipt.json')['transport']
        response=json.loads(receipt['body_text']) if receipt['http_status']==200 else {}
        usage=response.get('usage',{})
        records.append(dict(id=job['id'],phase=job['phase'],GT=job['GT'],attempt=request['attempt'],http_status=receipt['http_status'],
                            cost_or_reserve=account['cost_or_reserve_nano']/1e9,basis=account['basis'],
                            prompt_tokens=usage.get('prompt_tokens',0),completion_tokens=usage.get('completion_tokens',0),
                            reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0),
                            cache_cost=account['usage'].get('cost_with_official_cache_cny'),idle=account['usage'].get('idle')))
    ledger=c.read(c.OUT/'api_cost_ledger.json')
    assert abs(sum(r['cost_or_reserve'] for r in records)-ledger['used_or_reserved_cny'])<1e-8
    def aggregate(rows):
        return dict(attempts=len(rows),HTTP200=sum(r['http_status']==200 for r in rows),
                    cost_or_reserve_cny=sum(r['cost_or_reserve'] for r in rows),
                    mean_per_attempt_cny=statistics.mean([r['cost_or_reserve'] for r in rows]) if rows else 0,
                    prompt_tokens=sum(r['prompt_tokens'] for r in rows),completion_tokens=sum(r['completion_tokens'] for r in rows),
                    reasoning_tokens=sum(r['reasoning_tokens'] for r in rows),
                    idle_price_attempts=sum(r['idle'] is True for r in rows),busy_price_attempts=sum(r['idle'] is False for r in rows),
                    official_cache_price_estimate_cny=sum(r['cache_cost'] for r in rows) if all(r['cache_cost'] is not None for r in rows) else None)
    result=dict(total=aggregate(records),by_phase={phase:aggregate([r for r in records if r['phase']==phase]) for phase in ('quality','dispute')},
                retries=sum(r['attempt']>1 for r in records),unknown_or_inflight_cny=ledger['unknown_or_inflight_cny'],
                hard_cap_cny=20,no_GPU_cost=True,official_directory_not_channel_discount=True,
                cache_savings_not_used_for_budget=True,not_final_platform_invoice=True)
    c.put(c.OUT/'cost_summary.json',result)
    print(c.canonical(result))


if __name__=='__main__':main()
