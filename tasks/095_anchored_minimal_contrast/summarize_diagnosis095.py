from collections import Counter
import common095 as c
from diagnosis095 import entries

def main():
    root=c.lines(c.OUT/'root_source_review.jsonl');ind=c.lines(c.ROOT/'reviews/095_anchored_minimal_contrast/source_review.jsonl');private={r['id']:r for r in c.lines(c.PRIVATE/'diagnosis_cases.jsonl')};outside=c.lines(c.PRIVATE/'outside_discovery.jsonl');out=[]
    for r in root:out.append(dict(r,reviewer='root_executor',tags=[r['category']]))
    for r in ind:out.append(dict(id=r['id'],group=r['group'],GT=r['GT_unchanged'],B_raw=r['B_raw'],B_G=r['B_G'],reviewer=r['reviewer'],tags=r['tags'],interpretation=r['observation_zh'],citations=r['citations'],read_scope=r['scope'],outside_EHR_verified=False,new_medical_gold=False))
    assert len(out)==len({r['id'] for r in out})==80
    pid='d597fafc-7e27-65bc-aca9-c5275f7ba1a8';ref=private[pid]['reference'];es=entries(ref);entry=next(e for e in es if 'Note ID: 458866' in e)
    assert len(entry)>600
    supplemental=dict(id=pid,reference_id=3,note_id='458866',source_entry_sha256=c.h(entry),original_read_scope='first four ranked entries did not include entry3',supplement='完整C48回查发现目标日期已有相应动作记录，不能再说包内没有目标日期见证。该记录不能单独证明这是最早开始日；保持GT不变，不推断模型内部原因。',outside_claim=False)
    supplement_out=[]
    for r in outside:
        supplement_out.append(dict(id=r['id'],eligible_full_EHR_search_performed=True,policy='same patient/admission dates, exclude discharge summaries, fixed lexical discovery only',located_outside_C48_witness=False,result='target-day witness already inside C48; no new outside evidence established' if r['id']==pid else 'no specific outside witness established by limited search; unknown, not proof of absence',candidate_count=len(r['candidates'])))
    c.put(c.OUT/'source_review_supplement.json',dict(utc=c.now(),C48_recheck=supplemental,outside_search=supplement_out,limitations='Four targeted searches; not exhaustive full-EHR adjudication. No physician relabeling. Original source-review notes retained with this additive correction.'))
    c.putl(c.OUT/'source_review_80.jsonl',out);c.put(c.OUT/'source_review_80_summary.json',dict(N=80,patients=len({private[r['id']]['sid'] for r in out}),groups=dict(Counter(r['group'] for r in out)),GT=dict(Counter(r['GT'] for r in out)),reviewers=dict(Counter(r['reviewer'] for r in out)),tags=dict(Counter(tag for r in out for tag in r['tags'])),outside_verified_cases=0,limited_outside_queries=4,supplemental_C48_witnesses=1,scope='Purposive discovery sample, overlapping descriptive tags, not prevalence or new medical gold; all80 excluded from first and extension cohorts.'))
    print('80 source reviews combined; one C48 additive correction; outside verified=0, unknown retained')
if __name__=='__main__':main()
