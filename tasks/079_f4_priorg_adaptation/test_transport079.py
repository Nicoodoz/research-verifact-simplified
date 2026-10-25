"""Synthetic-only recovery tests, isolated from real task receipts and billing."""
from pathlib import Path
from unittest.mock import patch
import common079 as c
import run079 as r
REAL_OUT=c.OUT
class Fake:
 def __init__(self,statuses):self.statuses=list(statuses);self.calls=0
 def validate(self,body):pass
 def send(self,body):
  self.calls+=1;status=self.statuses.pop(0)
  return dict(http_status=status,body_text=c.canon(dict(usage=dict(prompt_tokens=100,completion_tokens=20))),outcome_unknown=status==0)
def one(name,statuses,expected,cap=None,parse_status='valid'):
 out=REAL_OUT/'synthetic_transport_tests'/name;out.mkdir(parents=True,exist_ok=False)
 body=dict(model=c.MODEL,max_tokens=100,messages=[dict(role='user',content='synthetic fixture, no patient')],enable_thinking=False,stream=False)
 job=dict(request_id='test_'+name,id='synthetic',sid='synthetic',arm='NV',stage='main',body=body,body_sha256=c.digest(body),scored=False,thinking=False)
 c.jl(out/'main_jobs.jsonl',[job]);fake=Fake(statuses)
 class CFG:api_key='synthetic-not-a-real-secret';base_url='https://synthetic.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
 with patch.object(c,'OUT',out),patch.object(r,'verify',lambda:None),patch.object(r,'load_config',lambda _:CFG()),patch.object(r,'DirectClient',lambda *a,**kw:fake),patch.object(c,'parse',lambda j,t:dict(model_returned=c.MODEL,status=parse_status)),patch.object(c,'CAP',cap if cap is not None else 20.):
  r.run(1);attempts,answers=r.state();assert fake.calls==expected
  if statuses==[0,200]:assert len(answers)==1 and len(attempts)==2 and abs(sum(x['cost_cny'] for x in attempts)-(c.bound(body)+.00048))<1e-12
  if expected==0:assert not attempts
  if parse_status=='invalid_core_fields':assert len(attempts)==1 and len(answers)==1
 return dict(test=name,synthetic_calls=fake.calls,status='PASS')
checks=[one('transient_recovery',[0,200],2),one('invalid_content_not_retried',[200],1,parse_status='invalid_core_fields'),one('budget_no_send',[200],0,cap=.00001),one('permission_failure_stops',[401],1)]
c.put(REAL_OUT/'transport_tests.json',dict(status='PASS',tests=checks,new_API_calls=0));print('4 synthetic transport tests PASS; no network')
