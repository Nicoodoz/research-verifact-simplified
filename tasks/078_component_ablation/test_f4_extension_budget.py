"""Verify cumulative cap includes prior078 spend; synthetic, zero network."""
from unittest.mock import patch
import run_f4_extension as r
c=r.c
out=c.OUT/'synthetic_budget_test'
out.mkdir(exist_ok=False)
job=c.lines(c.OUT/'main_jobs.jsonl')[0]
c.jl(out/'main_jobs.jsonl',[job])
c.put(out/'authorization.json',dict(old_spent_cny=34.999999))
class CFG:
    api_key='synthetic'
    base_url='https://synthetic.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
class Fake:
    def validate(self,b):pass
    def send(self,b):raise AssertionError('Cumulative budget must prevent this send')
with patch.object(c,'OUT',out),patch.object(r,'verify',lambda:None),patch.object(r,'load_config',lambda _:CFG()),patch.object(r,'DirectClient',lambda *a,**kw:Fake()):
    r.run(1)
    x=c.read(out/'execution_0000.json')
    assert x['stop_reason']=='task_budget_cap' and x['new_attempts']==0
    assert x['used_or_reserved_cny']==34.999999
c.put(c.OUT/'extension_budget_test.json',dict(status='PASS',new_API_calls=0,prior_spend_counted=True))
print('Cumulative cap synthetic test PASS; no network')
