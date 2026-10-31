"""Freeze512 actual120 training IDs and keep GT separate from GPU model inputs."""
from pathlib import Path
from collections import Counter
import json,hashlib
R=Path(__file__).resolve().parents[2];P=R/'.local_models/155_train_error_risk';P.mkdir(exist_ok=True)
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
source=rows(R/'.local_models/120_full_pool_sft/resume369/bundle/data/full_pool_sft120/train.jsonl');assert len(source)==2945 and len({str(r['sid']) for r in source})==32
evaluation_patients={str(r['sid']) for r in rows(R/'.local_models/134_author_baselines/keys.jsonl')};assert not evaluation_patients&{str(r['sid']) for r in source}
selected=[]
for g,n in [('Supported',256),('Not Supported',128),('Not Addressed',128)]:
    group=sorted([r for r in source if r['GT']==g],key=lambda r:hashlib.sha256(('train_error_risk|'+r['id']).encode()).hexdigest());assert len(group)>=n;selected+=group[:n]
inputs=[dict(id=r['id'],claim=r['claim'],reference=r['reference']) for r in selected]
keys=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],role='original120_train32') for r in selected]
assert len(inputs)==512 and all(set(r)=={'id','claim','reference'} for r in inputs)
(P/'inputs_source.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in inputs),encoding='utf-8')
(P/'keys.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in keys),encoding='utf-8')
O=R/'outputs/155_train_error_risk';O.mkdir(exist_ok=True)
result=dict(N=512,patients=len({r['sid'] for r in keys}),GT_counts=dict(Counter(r['GT'] for r in keys)),evaluation_patient_overlap=0,
    GT_in_model_inputs=False,source_pool_N=2945,source_pool_patients=32,source_weights='120_final369',prompt='136_claim_repeat',selection='class_stratified_SHA256(train_error_risk|ID)')
(O/'preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
