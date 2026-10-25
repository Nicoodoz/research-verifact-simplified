"""One source-locator repair before Judge, reuses all successful raw responses."""
from collections import Counter
import common094 as c
import api094,grounding094
def main():
    _,s=api094.state();inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};rows=[];public=[]
    for j in c.lines(c.PRIVATE/'extract_jobs.jsonl'):
        p=grounding094.parse(s[j['request_id']]['tr'],inputs[j['id']]['reference']);rows.append(dict(id=j['id'],arm=j['arm'],**p))
        public.append(dict(id=j['id'],arm=j['arm'],valid=p['valid'],status=p['record']['status'],candidate_count=len(p['record']['candidates']),citations=p['citations'],whitespace_normalizations=p['whitespace_normalizations'],record_sha256=c.h(c.canonical(p['record']))))
    c.putl(c.PRIVATE/'extracted_aligned.jsonl',rows);c.putl(c.OUT/'extraction_quality_aligned.jsonl',public)
    counts={a:dict(Counter(r['status'] for r in public if r['arm']==a)) for a in ['V','Q']}
    c.put(c.OUT/'source_alignment_gate.json',dict(utc=c.now(),status='PASS_SOURCE_LOCATOR_REPAIRED',counts=counts,valid={a:sum(r['valid'] for r in public if r['arm']==a) for a in ['V','Q']},whitespace_normalizations=sum(r['whitespace_normalizations'] for r in public),no_final_judge_yet=True,raw_sha256=c.sha(c.PRIVATE/'extracted_aligned.jsonl'),source_code_sha256=c.sha(c.TASK/'grounding094.py'),new_API_calls=0))
    print(counts)
if __name__=='__main__':main()
