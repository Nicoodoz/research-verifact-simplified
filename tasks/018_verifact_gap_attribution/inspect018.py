"""Small offline inspection helper; only reads frozen exposed-patient materials."""
import sys
import common018 as c
if sys.argv[1]=='shape':
    src,ps,_=c.prior.sources();s=src[0];p=next(iter(ps.values()))
    print(c.canonical(dict(passage_keys=list(p),passage={k:v for k,v in p.items() if k!='text'},ranking={k:v[:2] for k,v in s['rankings'].items()},score_sample=list(s['scores'].items())[:2])))
elif sys.argv[1]=='blocks':
    suffix=sys.argv[2];m=next(m for m in c.jsonlines(c.OUT/'preparation_001/materials.jsonl') if m['row']['case_id'].endswith(suffix))
    for b in c.blocks(m['references'][sys.argv[3]]):
        if int(sys.argv[4])==b['number']:print(c.canonical(b))
elif sys.argv[1]=='stats':
    from collections import Counter
    from diagnose018 import load_notes
    notes,_,_=load_notes();print(Counter(n['layer'] for n in notes))
