"""Reuse same-ID first native API receipts; no API calls, no quality computation."""
import common103 as c
from prompt103 import messages
m='qwen3.6-35b-a3b';public={r['id']:r for r in c.lines(c.OUT/'cohort240.jsonl') if r['local180']};private={r['id']:r for r in c.lines(c.PRIVATE/'sample240.jsonl')};preds={r['id']:r for r in c.lines(c.OUT/'predictions.jsonl')}
jobs={r['id']:r for r in c.lines(c.PRIVATE/'jobs_selected.jsonl') if r['model']==m and r['mode']=='native' and not r['repeat']}
usage={r['id']:r for r in c.lines(c.OUT/'usage.jsonl') if r['model']==m and r['mode']=='native' and not r['repeat']};result=[]
for pid,r in public.items():
 p=private[pid];j=jobs[pid];u=usage[pid];b=j['body'];q=preds[pid]
 assert c.digest(p['claim'])==r['claim_sha256'] and c.digest(p['reference'])==r['reference_sha256']
 assert b['model']==m and b['messages']==messages(p['claim'],p['reference'],'native')
 assert b['enable_thinking'] and b['thinking_budget']==4096 and b['max_tokens']==768 and b['temperature']==0
 assert u['request_id']==j['request_id'] and u['valid'] and u['finish_reason']=='stop'
 assert q['claim_sha256']==r['claim_sha256'] and q['reference_sha256']==r['reference_sha256']
 parsed=q['arms'][m+'__native'];assert parsed['verdict'] in c.LABELS
 result.append(dict(id=pid,model=m,arm='native_api',parsed=parsed,request_id=j['request_id'],body_sha256=c.digest(c.canonical(b)),claim_sha256=r['claim_sha256'],reference_sha256=r['reference_sha256'],origin='103 first-stage valid native API receipt',local_weight_revision_equivalence_not_asserted=True))
assert len(result)==180
c.putl(c.OUT/'native_api_reuse180.jsonl',result)
c.put(c.OUT/'native_api_reuse_manifest.json',dict(model=m,N=180,new_API_calls=0,new_GPU_native_calls=0,inputs_and_settings_checked=True,API_revision_unknown=True,training_increment='local lora_label minus local label_base only',source=c.sha(c.OUT/'native_api_reuse180.jsonl')))
print('180 original valid native API replies verified; zero new calls; no quality metrics computed')
