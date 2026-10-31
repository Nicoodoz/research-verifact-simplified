"""Add a training-only conditional-plan NA example to the exact149 extracted pair."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[2];P=R/'.local_models/152_demo_na';P.mkdir(exist_ok=True)
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
examples=rows(R/'.local_models/149_demo_extract/examples.jsonl');assert len(examples)==2
wanted='eec5864a-fa13-48a6-37db-ebfbc0fb3aa8'
train=rows(R/'.local_models/127_native_reason_data/dataset_v12_support20261031/paired/train_verdict_reason.jsonl')
r=next(r for r in train if r['id']==wanted);assert r['GT']=='Not Addressed' and r['role']=='train'
actual={r['id'] for r in rows(R/'.local_models/120_full_pool_sft/resume369/bundle/data/full_pool_sft120/train.jsonl')}
assert wanted in actual
patients={str(r['sid']) for r in rows(R/'.local_models/134_author_baselines/keys.jsonl')}
assert str(r['sid']) not in patients and str(r['sid']) not in {str(x['sid']) for x in examples}
ref=r['reference'];matches=list(re.finditer(r'(?m)^(\d+)\. Date: ',ref));selected={}
for source in r['reason_metadata']['evidence_sources']:
    if source['kind']!='reference_span':continue
    assert ref[source['start']:source['end']]==source['quote']
    for n,h in enumerate(matches):
        end=matches[n+1].start() if n+1<len(matches) else len(ref)
        if h.start()<source['end'] and end>source['start']:selected[int(h.group(1))]=ref[h.start():end]
assert set(selected)=={33,78}
excerpt=ref[:matches[0].start()]+'\n'.join(selected[n].rstrip() for n in sorted(selected))
new=dict(id=r['id'],sid=r['sid'],GT=r['GT'],claim=r['claim'],reference=excerpt,answer=json.dumps({'verdict':r['GT']},separators=(',',':')))
examples.append(new)
(P/'examples.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in examples),encoding='utf-8')
O=R/'outputs/152_demo_na';O.mkdir(exist_ok=True)
result=dict(example_ids=[r['id'] for r in examples],labels=[r['GT'] for r in examples],original149_pair_unchanged=True,
    added_example_id=wanted,added_example_original_GT='Not Addressed',added_source_units=[33,78],
    full_reference_characters=len(ref),excerpt_reference_characters=len(excerpt),in_actual120_training=True,
    target_reference_changed=False,evaluation_patient_used_as_demo=False)
(O/'preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
