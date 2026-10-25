"""Metadata/usage-only check of the first actual Judge responses, never GT/performance."""
import itertools,json
from collections import Counter
import common036 as c
import api036 as a
def main():
    out=c.OUT/'service_health_001.json';assert not out.exists();rows=[]
    with (c.OUT/'judge_inputs_001/jobs.jsonl').open(encoding='utf-8') as stream:
        for line in itertools.islice(stream,200):
            j=json.loads(line);folder=c.OUT/'attempts'/(c.digest(j['request_id'])[:24]+'_01');path=folder/'receipt.json'
            if not path.exists():continue
            tr=c.read(path)['transport'];response=json.loads(tr['body_text']) if tr['http_status']==200 else {};u=response.get('usage',{});amount,basis=a.charge(j,tr)
            rows.append(dict(request_id=j['request_id'],role=j['role'],HTTP=tr['http_status'],returned_model=response.get('model'),usage=u,estimated_cny=amount,cost_basis=basis,receipt_sha256=c.sha(path)))
    assert len(rows)>=50 and all(r['HTTP']==200 and r['returned_model']=='deepseek-v4-flash-0731' for r in rows)
    average=sum(r['estimated_cny'] for r in rows)/len(rows);config=a.api.load_config(c.ROOT/'.env.aliyun');registered=c.read(c.OUT/'evaluation_freeze_001/service_registration.json');assert config.base_url==registered['aliyun_base_url']
    summary=dict(n=len(rows),returned_models=dict(Counter(r['returned_model'] for r in rows)),mean_peak_estimated_cny=average,GT_read=False,performance_evaluated=False,API_calls_added=0,endpoint_matches_registration=True)
    c.put(out,dict(created_utc=c.now(),summary=summary,rows=rows));print(summary)
if __name__=='__main__':main()
