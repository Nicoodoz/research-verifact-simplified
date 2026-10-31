"""Freeze six original-training examples by model error and actual margin."""
from pathlib import Path
import json,re,hashlib
R=Path(__file__).resolve().parents[2];P=R/'.local_models/162_train_demo_pool'
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def main():
    if (P/'candidates.jsonl').exists():raise FileExistsError('Preserve162 candidates')
    source=R/'.local_models/155_train_error_risk';keys={r['id']:r for r in rows(source/'keys.jsonl')};inputs={r['id']:r for r in rows(source/'inputs_source.jsonl')}
    raw={r['id']:r for r in (json.loads(f.read_text()) for f in (source/'evidence/results/native_train').glob('*.json'))}
    actual={r['id']:r for r in rows(R/'.local_models/120_full_pool_sft/resume369/bundle/data/full_pool_sft120/train.jsonl')}
    old=rows(R/'.local_models/152_demo_na/examples.jsonl');used={str(r['sid']) for r in old};evaluation={str(r['sid']) for r in rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    chosen=[];metadata=[]
    for gt in ('Supported','Not Supported','Not Addressed'):
        available=[i for i,k in keys.items() if k['GT']==gt]
        order=sorted(available,key=lambda i:(raw[i]['parsed']['verdict']==gt,raw[i]['native_margin'] if gt=='Supported' else -raw[i]['native_margin'],i))
        selected=[]
        for i in order:
            k=keys[i];sid=str(k['sid'])
            if sid in used:continue
            assert k['role']=='original120_train32' and sid not in evaluation
            assert i in actual and actual[i]['GT']==gt and str(actual[i]['sid'])==sid
            assert inputs[i]['claim']==actual[i]['claim'] and inputs[i]['reference']==actual[i]['reference']
            r=inputs[i];ref=r['reference'];heads=list(re.finditer(r'(?m)^(\d+)\. Date: ',ref));assert heads
            units=[dict(number=int(m.group(1)),text=ref[m.start():heads[n+1].start() if n+1<len(heads) else len(ref)]) for n,m in enumerate(heads)]
            chosen.append(dict(id=i,sid=sid,GT=gt,role=k['role'],claim=r['claim'],reference=ref,prefix=ref[:heads[0].start()],units=units))
            metadata.append(dict(id=i,sid=sid,GT=gt,native_verdict=raw[i]['parsed']['verdict'],native_margin=raw[i]['native_margin'],source='155 original120 train32',reference_characters=len(ref),units=len(units),reference_sha256=hashlib.sha256(ref.encode()).hexdigest()))
            used.add(sid);selected.append(i)
            if len(selected)==2:break
        assert len(selected)==2
    P.mkdir(exist_ok=True);(P/'candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in chosen),encoding='utf-8')
    O=R/'outputs/162_train_demo_pool';O.mkdir(exist_ok=True);(O/'selection.json').write_text(json.dumps(dict(N=6,training_only=True,GT_changed=False,evaluation_used=False,candidates=metadata),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False))

if __name__=='__main__':main()
