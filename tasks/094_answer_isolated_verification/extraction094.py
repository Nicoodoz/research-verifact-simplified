"""Validate source citations before any final verdict; expose only review diagnostics."""
from collections import Counter
import common094 as c
import api094,method094 as m
def main():
    _,s=api094.state();inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};rows=[];public=[]
    for j in c.lines(c.PRIVATE/'extract_jobs.jsonl'):
        tr=s[j['request_id']]['tr'];p=m.parse_qa(tr,inputs[j['id']]['reference']);rows.append(dict(id=j['id'],arm=j['arm'],**p))
        public.append(dict(id=j['id'],arm=j['arm'],valid=p['valid'],status=p['record']['status'],candidate_count=len(p['record']['candidates']),citations=p['citations'],record_sha256=c.h(c.canonical(p['record']))))
        if not p['valid']:print('INVALID',j['id'],j['arm'],m.obj(tr),flush=True)
    c.putl(c.PRIVATE/'extracted_records.jsonl',rows);c.putl(c.OUT/'extraction_quality.jsonl',public)
    counts={a:dict(Counter(r['status'] for r in public if r['arm']==a)) for a in ['V','Q']}
    c.put(c.OUT/'extraction_gate.json',dict(utc=c.now(),status='SOURCE_VALIDATION_COMPLETE',counts=counts,valid={a:sum(r['valid'] for r in public if r['arm']==a) for a in ['V','Q']},no_final_judge_yet=True,raw_sha256=c.sha(c.PRIVATE/'extracted_records.jsonl'),jobs_sha256=c.sha(c.PRIVATE/'extract_jobs.jsonl')))
    print(counts,flush=True)
if __name__=='__main__':main()
