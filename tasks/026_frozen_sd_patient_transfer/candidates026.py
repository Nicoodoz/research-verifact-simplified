"""Freeze conditional Qwen whitelist from new DeepSeek scores; never reads GT."""
from collections import Counter
import common026 as c
def run():
    c.require(not (c.OUT/'live.lock').exists(),'D stage still running');jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);counts=Counter(a['request_id'] for a in attempts);d=[j for j in jobs if j['model_key']=='deepseek']
    c.require(all(j['request_id'] in term or counts[j['request_id']]>=3 for j in d),'Complete D attempts first')
    candidates=[];invalid=[];records=[]
    for j in d:
        if j['arm']!='S':continue
        v=term.get(j['request_id'])
        if not v or v['status'] not in c.VALID:invalid.append(j['proposition_id']);continue
        u0=int(c.risk.decode(c.risk.logs(v['scores']),0));u2=int(c.risk.decode(c.risk.logs(v['scores']),2));candidate=u0!=0 and u2==0
        if candidate:candidates.append(j['proposition_id'])
        records.append(dict(proposition_id=j['proposition_id'],D_request_id=j['request_id'],U0=c.LABELS[u0],U2=c.LABELS[u2],candidate=candidate))
    out=c.OUT/'candidate_freeze';out.mkdir(exist_ok=False);c.put(out/'candidates.json',dict(created_utc=c.now(),candidate_ids=candidates,invalid_D_scoring_ids=invalid,GT_used=False,records=records))
    deps=[c.OUT/'preparation_001/manifest.json',c.OUT/'gate_freeze/manifest.json',c.TASK/'candidates026.py',out/'candidates.json']+list((c.OUT/'attempts').glob('*/*.json'))
    c.put(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps}))
    print(c.canonical(dict(candidates=len(candidates),invalid_D_scoring=len(invalid),GT_used=False)))
if __name__=='__main__':run()
