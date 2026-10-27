"""Freeze8 long-input training-only resource cases without inspecting model outputs."""
import common103 as c
rows=[r for r in c.lines(c.PRIVATE/'eligible.jsonl') if r['role']=='train']
lengths={r['id']:r['label'] for r in c.lines(c.OUT/'token_lengths.jsonl') if r['model']=='qwen3.5-9b'}
other={r['id']:r['label'] for r in c.lines(c.OUT/'token_lengths.jsonl') if r['model']=='qwen3.6-35b-a3b'}
chosen=[];seen=set()
for r in sorted(rows,key=lambda r:(-lengths[r['id']],r['id'])):
 if r['sid'] in seen:continue
 chosen.append(r);seen.add(r['sid'])
 if len(chosen)==8:break
roles=c.read(c.OUT/'patient_roles.json')['patients']
assert len(chosen)==8 and seen<=set(roles['train']) and not seen&set(roles['selection']+roles['confirmation'])
assert all(lengths[r['id']]==other[r['id']] for r in chosen)
target=c.PRIVATE/'resource_tail8.jsonl';c.putl(target,chosen)
c.put(c.OUT/'resource_tail_freeze.json',dict(utc=c.utc(),selection='Longest full published input per training patient, descending length thenID; top8 distinct training patients; no GT or predictions as features',resource_only=True,formal_training512_unchanged=True,probe_weights_discarded=True,sha256=c.sha(target),rows=[dict(id=r['id'],sid=r['sid'],label_input_tokens=lengths[r['id']],claim_sha256=c.digest(r['claim']),reference_sha256=c.digest(r['reference'])) for r in chosen]))
print('Frozen8 distinct training patients, max input',max(lengths[r['id']] for r in chosen))
