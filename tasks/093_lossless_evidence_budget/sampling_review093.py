"""Describe the frozen sampling/operation coverage; never changes selected IDs."""
from collections import Counter
import common093 as c
def main():
    sample=c.lines(c.OUT/'sample.jsonl');pool=c.lines(c.PRIVATE/'pool_inputs.jsonl');natural=[r for r in sample if r['panel']=='natural']
    strict={r['id'] for r in sorted(pool,key=lambda r:(c.h('093/natural/'+r['id']),r['id']))[:len(natural)]}
    selected={r['id'] for r in natural}
    summary=dict(natural_matches_standalone_first_hash_prefix=selected==strict,natural_displaced_ids=sorted(strict-selected),natural_replacement_ids=sorted(selected-strict),panels={p:dict(authors=dict(Counter(r['author'] for r in sample if r['panel']==p)),operation_patients=sorted({r['sid'] for r in sample if r['panel']==p and r['A_added']}),operated_GT=dict(Counter(r['GT'] for r in sample if r['panel']==p and r['A_added'])),patient_counts=dict(Counter(r['sid'] for r in sample if r['panel']==p))) for p in ['natural','pressure']},note='Natural/pressure selected in fixed 3:1 blocks with de-duplication. Any diverted natural prefix IDs are disclosed, never resampled after answers.')
    c.put(c.OUT/'sampling_review.json',summary);print({k:v for k,v in summary.items() if k!='panels'})
if __name__=='__main__':main()
