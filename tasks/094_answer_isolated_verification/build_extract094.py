"""Only reviewed questions enter matched V/Q extraction."""
import json
import common094 as c
import method094 as m
from prepare094 import job
def main():
    review=c.read(c.OUT/'question_review.json');inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};qs=c.lines(c.PRIVATE/'questions_reviewed.jsonl');sample=c.lines(c.OUT/'sample.jsonl');jobs=[];coverage={}
    allowed=set(review['accepted_ids'])
    assert allowed<=set(q['id'] for q in qs if q['valid'])
    for panel,minimum in [('natural',.8),('mechanism',.75)]:
        rows=[r for r in sample if r['panel']==panel];coverage[panel]=dict(N=len(rows),operated=sum(r['id'] in allowed for r in rows));assert coverage[panel]['operated']/len(rows)>=minimum
    for q in qs:
        if q['id'] not in allowed:continue
        r=inputs[q['id']]
        v=m.qa_body(r,q,'V');b=m.qa_body(r,q,'Q');vp=json.loads(v['messages'][1]['content']);qp=json.loads(b['messages'][1]['content']);assert vp.pop('unverified_claim')==r['text'] and vp==qp
        assert set(qp)=={'question','reference'} and qp['reference']==r['reference']
        for arm,body in [('V',v),('Q',b)]:
            j=job(r['id'],'extract',arm,body);assert j['bound_cny']<=c.read(c.OUT/'design_freeze.json')['allocations'][r['id']]['extract_'+arm];jobs.append(j)
    c.putl(c.PRIVATE/'extract_jobs.jsonl',jobs);c.put(c.OUT/'question_gate.json',dict(status='PASS',coverage=coverage,GT_in_review=False,question_sha256=c.sha(c.PRIVATE/'questions_reviewed.jsonl'),review_sha256=c.sha(c.OUT/'question_review.json'),jobs_sha256=c.sha(c.PRIVATE/'extract_jobs.jsonl'),utc=c.now()))
    print('Question gate',coverage,'extract requests',len(jobs))
if __name__=='__main__':main()
