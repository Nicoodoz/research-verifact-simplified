"""Local CPU extraction from two already reviewed training examples; no evaluation text read."""
from pathlib import Path
import json,re,hashlib
R=Path(__file__).resolve().parents[2];P=R/'.local_models/149_demo_extract';P.mkdir(exist_ok=True)
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
source=rows(R/'.local_models/141_two_demos/screen160/bundle/data/examples.jsonl')
review={r['id']:r for r in rows(R/'.local_models/127_native_reason_data/dataset_v12_support20261031/paired/train_verdict_reason.jsonl')}
eval_patients={str(r['sid']) for r in rows(R/'.local_models/134_author_baselines/keys.jsonl')}
result=[];details=[]
for old in source:
    r=review[old['id']];assert str(r['sid']) not in eval_patients and r['role']=='train'
    assert old['claim']==r['claim'] and old['reference']==r['reference']
    wanted={s['display_number'] for e in r['reason_metadata']['evidence_sources'] if e['kind']=='reference_span' for s in e['rendered_sources']}
    ref=old['reference'];headers=list(re.finditer(r'(?m)^(\d+)\. Date: ',ref));units={}
    assert headers
    for n,m in enumerate(headers):units[int(m.group(1))]=ref[m.start():headers[n+1].start() if n+1<len(headers) else len(ref)]
    assert wanted<=units.keys() and len(wanted)==4
    excerpt=ref[:headers[0].start()]+'\n'.join(units[n].rstrip() for n in sorted(wanted))
    out=dict(old,reference=excerpt);result.append(out)
    details.append(dict(id=old['id'],label=old['GT'],selected_display_numbers=sorted(wanted),
        full_reference_characters=len(ref),excerpt_reference_characters=len(excerpt),original_unit_count=len(units),excerpt_unit_count=len(wanted),
        exact_full_units_preserved=True,training_patient=True,claim_and_label_unchanged=True))
(P/'examples.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in result),encoding='utf-8')
O=R/'outputs/149_demo_extract';O.mkdir(exist_ok=True)
(O/'preparation.json').write_text(json.dumps(dict(method='demo_extract',N_examples=2,details=details,target_reference_changed=False,GT_changed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(details,ensure_ascii=False))
