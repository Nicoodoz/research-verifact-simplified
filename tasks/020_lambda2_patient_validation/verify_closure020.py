import json
import common020 as c
from io020 import load_phase
O=c.OUT
result={}
for st in ['new10_embedding','new10_rerank','new10_judge']:
    v,a=load_phase(st)
    result[st]={'jobs':len(v),'received':sum(x['status']=='received' for x in v.values()),'attempt_records':len(a)}
for mf in [O/'new10_embedding/receipt_manifest.json',O/'new10_rerank/receipt_manifest.json',O/'new10_judge/receipt_manifest.json',O/'analysis_001/manifest.json']:
    m=c.read(mf);bad=[]
    for n,h in m['sha256'].items():
        p=c.ROOT/n
        if c.file_hash(p)!=h:bad.append(n)
    result[mf.relative_to(O).as_posix()]={'entries':len(m['sha256']),'bad':bad}
ledger=c.read(O/'live_ledger.json')
result['budget']={'used_or_reserved_cny':ledger['used_or_reserved_cny'],'cap_cny':ledger['cap_cny'],'within_cap':ledger['used_or_reserved_cny']<=ledger['cap_cny']}
result['reserved_test_used']=c.read(O/'analysis_001/decision.json')['reserved_test_used']
print(json.dumps(result,ensure_ascii=False))
