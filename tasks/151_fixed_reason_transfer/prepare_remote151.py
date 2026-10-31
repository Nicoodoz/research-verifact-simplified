"""Freeze300 new fixed-label rationale inputs, reusing the exact147 generator prompt."""
from pathlib import Path
import json,sys,hashlib,time
BASE=Path('/root/autodl-tmp');P=BASE/'verifact151_fixed_reason_transfer'
if (P/'inputs.jsonl').exists():raise FileExistsError('151 already prepared')
P.mkdir(exist_ok=True);old=json.loads((BASE/'verifact147_fixed_reason/selection.json').read_text());excluded=set(old['ids'])
inputs={};pred={}
for scope in ('screen160','old500','full1817'):
    p=BASE/('verifact136_claim_repeat_'+scope)
    for s in (p/'data/inputs.jsonl').read_text().splitlines():
        r=json.loads(s);inputs[r['id']]=r
    for f in (p/'results/claim_repeat').glob('*.json'):
        r=json.loads(f.read_text())
        if r.get('parsed',{}).get('valid'):pred[r['id']]=r['parsed']['verdict']
assert len(inputs)==1817 and len(pred)==1817
ids=sorted(set(inputs)-excluded,key=lambda i:hashlib.sha256(('fixed_reason_transfer|'+i).encode()).hexdigest())[:300]
rows=[dict(id=i,claim=inputs[i]['claim'],reference=inputs[i]['reference'],fixed_verdict=pred[i]) for i in ids]
assert not set(ids)&excluded and all(set(r)=={'id','claim','reference','fixed_verdict'} for r in rows)
(P/'inputs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
(P/'selection.json').write_text(json.dumps(dict(N=300,ids=ids,excluded147_N=60,GT_used=False,predicted_label_counts={g:sum(r['fixed_verdict']==g for r in rows) for g in set(pred.values())},prepared_epoch=time.time()),indent=2)+'\n',encoding='utf-8')
worker=(BASE/'verifact147_fixed_reason/worker147.py').read_text()
worker=worker.replace('started+3600','started+1800').replace("for arm in ('reason120','reason_base9b'):","for arm in ('reason_base9b',):")
worker=worker.replace("N=60,arms=['reason120','reason_base9b']","N=300,arms=['reason_base9b']").replace('total=120','total=300')
(P/'worker151.py').write_text(worker,encoding='utf-8')
print(json.dumps(json.loads((P/'selection.json').read_text())))
