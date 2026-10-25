"""Freeze 80 source-review cases with correct protections; no API or new medical gold."""
import re,math
from collections import Counter
import common095 as c
def words(s):return set(re.findall(r'[a-z]{3,}|\d+(?:\.\d+)?',s.lower()))-set('the and with was were from that this patient had has she his her for'.split())
def entries(ref):
    starts=list(re.finditer(r'(?m)^\d+\. Date:',ref))
    return [ref[m.start():starts[i+1].start() if i+1<len(starts) else len(ref)] for i,m in enumerate(starts)]
def main():
    cached=c.lines(c.OUT/'cache_selected.jsonl');meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};inp={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    usable=[r for r in cached if r['parsed']['valid']];used=set();selected=[]
    conditions=[('raw_correct_G_wrong',16,lambda r:r['labels']['raw']==meta[r['id']]['GT'] and r['labels']['PriorG']!=meta[r['id']]['GT']),('G_correct_raw_wrong',12,lambda r:r['labels']['raw']!=meta[r['id']]['GT'] and r['labels']['PriorG']==meta[r['id']]['GT']),('author_correct_B_wrong',16,lambda r:meta[r['id']]['original']==meta[r['id']]['GT'] and r['labels']['PriorG']!=meta[r['id']]['GT']),('B_correct_author_wrong',12,lambda r:meta[r['id']]['original']!=meta[r['id']]['GT'] and r['labels']['PriorG']==meta[r['id']]['GT']),('both_wrong',12,lambda r:meta[r['id']]['original']!=meta[r['id']]['GT'] and r['labels']['PriorG']!=meta[r['id']]['GT']),('correct_protection',12,lambda r:meta[r['id']]['original']==meta[r['id']]['GT'] and r['labels']['PriorG']==meta[r['id']]['GT'])]
    patient=Counter();labels=Counter()
    for group,n,predicate in conditions:
        for _ in range(n):
            available=[r for r in usable if r['id'] not in used and predicate(r)]
            assert available,group
            r=min(available,key=lambda r:(labels[group,meta[r['id']]['GT']],patient[meta[r['id']]['sid']],c.h('095/diagnosis/'+r['id'])))
            pid=r['id'];used.add(pid);patient[meta[pid]['sid']]+=1;labels[group,meta[pid]['GT']]+=1
            selected.append(dict(group=group,**meta[pid],B_raw=r['labels']['raw'],B_G=r['labels']['PriorG'],scores=r['parsed']['scores']))
    private=[];public=[]
    for i,r in enumerate(selected):
        x=inp[r['id']];es=entries(x['reference']);cw=words(x['text']);idf={w:1+math.log((1+len(es))/(1+sum(w in words(e) for e in es))) for w in cw}
        ranked=sorted(enumerate(es,1),key=lambda p:(-sum(idf[w] for w in cw&words(p[1])),-len(cw&words(p[1])),p[0]))
        review_owner='root' if i%2==0 else 'independent_source_reviewer'
        private.append(dict(**r,claim=x['text'],reference=x['reference'],source=x['source'],review_owner=review_owner,relevant_entries=[dict(reference_id=j,text=e) for j,e in ranked[:4]]))
        public.append(dict(**r,review_owner=review_owner,claim_sha256=c.h(x['text']),reference_sha256=c.h(x['reference'])))
    c.putl(c.PRIVATE/'diagnosis_cases.jsonl',private);c.putl(c.OUT/'diagnosis_sample.jsonl',public);c.put(c.OUT/'diagnosis_freeze.json',dict(utc=c.now(),N=80,patients=len(patient),groups=dict(Counter(r['group'] for r in public)),GT=dict(Counter(r['GT'] for r in public)),source_sha256=c.sha(c.PRIVATE/'diagnosis_cases.jsonl'),sampling_code_sha256=c.sha(c.TASK/'diagnosis095.py'),scope='Discovery, not confirmation; 40 root +40 separate source reviewer; unknown allowed; no GT sent to API'))
    print('Diagnostic review',len(public),'patients',len(patient))
if __name__=='__main__':main()
