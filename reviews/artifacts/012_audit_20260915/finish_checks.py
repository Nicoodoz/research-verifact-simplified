from pathlib import Path
from unittest.mock import patch
from collections import defaultdict
import json,sys,re,hashlib
R=Path('D:/Research-VeriFact');O=R/'outputs/012_comparative_error_diagnosis';T=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tasks/012_comparative_error_diagnosis'));import study012 as s
from evidence012 import trace
from inspect_references import blocks,normalized
packets=s.pilot.jsonl(O/'materials_001/packets.jsonl');groups=defaultdict(list)
for p in packets:
    for arm,ref in p['input']['references'].items():
        for b in blocks(ref):
            key=s.pilot.fingerprint([p['row']['subject_id'],b['date'],b['time'],b['category'],b['description'],b['note_id'],normalized(b['text'])])
            groups[key].append((p['row']['case_id'],arm,b['number'],b['text']))
collisions=[v for v in groups.values() if len({x[3] for x in v})>1]
summary={'reading_dedup_normalizes_whitespace':True,'groups_with_nonidentical_text_after_normalized_match':len(collisions),
    'affected_cases':sorted({x[0] for v in collisions for x in v}),
    'literal_reference_payloads_preserved':True}
# Isolated negative probes of the actual strict manifest checker.
root=T/'freeze_fixture';root.mkdir();out=root/'run';out.mkdir();inp=root/'input.json';code=root/'compute.py';pred=out/'pred.json'
for p in (inp,code,pred):p.write_text('original',encoding='utf-8')
rejected=[]
with patch.object(s,'ROOT',root):
    s.seal(out,[inp],[code]);s.check(out)
    (root/'reviews').mkdir();(root/'reviews/README.md').write_text('normal audit update',encoding='utf-8');s.check(out)
    for p in (inp,code,pred):
        old=p.read_bytes();p.write_bytes(old+b' changed')
        try:s.check(out)
        except AssertionError:rejected.append(p.name)
        else:raise AssertionError('Tamper accepted')
        p.write_bytes(old);s.check(out)
try:trace({'subject_id':'A'},[],{'SUBJECT_ID':'B','TEXT':'finding'},0,3)
except AssertionError:rejected.append('cross_patient_trace')
else:raise AssertionError('Cross-patient trace accepted')
summary.update(negative_controls_rejected=rejected,mutable_audit_document_allowed=True)
assert len(rejected)==4
# These selected display groups are only a rendering concern, never a method output.
(T/'finish_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
