"""Independent synthetic tariff boundary checks; never touches task ledger."""
import json,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/095_anchored_minimal_contrast'))
import pricing095 as p
tests=[('22_exact','2026-09-27T22:00:00+08:00','2026-09-27T22:01:00+08:00',True),('early_morning','2026-09-28T07:58:00+08:00','2026-09-28T07:59:59+08:00',True),('08_exact','2026-09-28T07:59:00+08:00','2026-09-28T08:00:00+08:00',False),('cross_22','2026-09-27T21:59:00+08:00','2026-09-27T22:01:00+08:00',False),('midnight','2026-09-27T23:59:00+08:00','2026-09-28T00:01:00+08:00',True),('UTC','2026-09-27T14:01:00+00:00','2026-09-27T14:02:00+00:00',True),('naive','2026-09-27T23:01:00','2026-09-27T23:02:00',False),('backward','2026-09-27T23:02:00+08:00','2026-09-27T23:01:00+08:00',False),('long','2026-09-27T23:01:00+08:00','2026-09-28T02:01:00+08:00',False),('different_window','2026-09-27T23:01:00+08:00','2026-09-28T23:02:00+08:00',False)]
res=[]
for name,start,end,expected in tests:
    actual=p.inside_one_idle_window({'started_utc':start,'ended_utc':end});assert actual==expected
    res.append({'name':name,'passed':True})
j={'bound_cny':1}; tr={'http_status':200,'started_utc':'2026-09-27T23:01:00+08:00','ended_utc':'2026-09-27T23:02:00+08:00','body_text':json.dumps({'model':'deepseek-v4-flash-0731','usage':{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':200}}})}
assert abs(p.charge(j,tr)-.00168)<1e-12
assert p.charge(j,None)==1
unknown=dict(tr,http_status=0)
res.append({'name':'unknown_with_usage_must_keep_bound','passed':p.charge(j,unknown)==1,'observed':p.charge(j,unknown),'expected':1,'synthetic_only':True})
out={'code_sha256':hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),'tests':res}
dest=Path(__file__).parent/'pricing_checks_initial.json'
with dest.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(out)
