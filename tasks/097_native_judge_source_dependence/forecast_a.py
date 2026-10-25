"""Forecast only; never use outcome content."""
import json,statistics
import common097 as c

def main():
    panel=c.lines(c.OUT/'a_panel.jsonl'); jobs=c.lines(c.PRIVATE/'a_jobs.jsonl')
    usage=[]
    for r in panel:
        rec=c.read(c.ROOT/r['B_receipt_path'])
        tr=rec.get('transport',rec)
        if tr['http_status']!=200:continue
        u=json.loads(tr['body_text'])['usage']
        usage.append(dict(inp=u['prompt_tokens'],out=u['completion_tokens'],cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0),ratio=u['prompt_tokens']/len(c.read(c.ROOT/r['B_request_path'])['job']['body']['messages'][1]['content'])))
    # Use actual template prefix plus published/reference UTF-8 length, then conservative p95 historical output for all arms.
    p95=sorted(x['out'] for x in usage)[int(.95*(len(usage)-1))]
    ratio=max(x['ratio'] for x in usage)
    estimates=[]
    for j in jobs:
        n=len(j['body']['messages'][0]['content'])+len(j['body']['messages'][1]['content'])
        inp=n*ratio+1000
        estimates.append((inp*3+p95*9)/1e6)
    result=dict(N=len(panel),new_request_count=len(jobs),historical_B_usage=dict(input_mean=statistics.mean(x['inp'] for x in usage),completion_mean=statistics.mean(x['out'] for x in usage),completion_p95=p95,cached_mean=statistics.mean(x['cached'] for x in usage),input_chars_to_tokens_max=ratio),forecast_busy_no_cache_cny=sum(estimates),forecast_assumptions='Worst observed prompt token/characters ratio on sampled B user prompt, +1000 tokens envelope; each new call p95 historic B completion; no cache discount; actual cap enforced per request with max output 8192 and remaining balance',full_max_token_bound=sum(j['bound_cny'] for j in jobs),hard_cap_cny=20,reserve_cny=2)
    c.write_json(c.OUT/'a_forecast.json',result);print(result)
if __name__=='__main__':main()
