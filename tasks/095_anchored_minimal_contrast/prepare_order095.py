import json,copy
import common095 as c
import state095 as s
from prepare_baseline095 import make_job
from workflow095 import verify_freeze

def main():
    verify_freeze();assert c.read(c.OUT/'screen_numeric_decision.json')['provisional_numeric_action']=='one_frozen_extension'
    sample=c.lines(c.OUT/'screen_sample.jsonl');checked={r['id']:r for r in c.lines(c.PRIVATE/'checked.jsonl')};aliases={(r['id'],r['arm']):r for r in c.lines(c.OUT/'screen_aliases.jsonl')};success=s.successful_jobs();jobs=[];mapping=[]
    for panel in ['natural','mechanism']:
        chosen=sorted([r for r in sample if r['panel']==panel and checked[r['id']]['operated']],key=lambda r:c.h('095/order/'+r['id']))[:12]
        for r in chosen:
            a=aliases[r['id'],'C'];old=success[a['request_id']]['job']['body'];body=copy.deepcopy(old);p=json.loads(body['messages'][1]['content']);new={k:p[k] for k in ['proposition','reference','auxiliary_anchor_excerpts','alternative_hypothesis']};body['messages'][1]['content']=json.dumps(new,ensure_ascii=False,separators=(',',':'))
            assert json.loads(old['messages'][1]['content'])==json.loads(body['messages'][1]['content']);assert old['messages'][1]['content']!=body['messages'][1]['content']
            j=make_job(r['id'],'method','C_order',body);jobs.append(j);mapping.append(dict(id=r['id'],panel=panel,C_request_id=a['request_id'],order_request_id=j['request_id']))
    c.putl(c.PRIVATE/'order_jobs.jsonl',jobs);c.putl(c.OUT/'order_aliases.jsonl',mapping);c.put(c.OUT/'order_freeze.json',dict(utc=c.now(),N=len(jobs),protocol_sha256=c.sha(c.TASK/'order_control_protocol.md'),code_sha256=c.sha(c.TASK/'prepare_order095.py'),jobs_sha256=c.sha(c.PRIVATE/'order_jobs.jsonl'),selection='fixed hash of operated IDs, 12 per panel, no prediction filter',max_bound_cny=sum(j['bound_cny'] for j in jobs)))
if __name__=='__main__':main()
