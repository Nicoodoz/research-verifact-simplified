"""Before paid construction: all selected source headers and offsets are readable."""
import re
import common095 as c
import method095 as m
from collections import Counter
rows=c.lines(c.PRIVATE/'screen_inputs.jsonl');jobs=c.lines(c.PRIVATE/'construct_jobs.jsonl');byid={j['id']:j for j in jobs};counts=Counter()
for r in rows:
    refs=m.entries(r['reference']);assert len(refs)==len(re.findall(r'(?m)^\d+\. Date:',r['reference']))>0
    for ref in refs.values():assert r['reference'][ref['offset']:ref['offset']+len(ref['text'])]==ref['text']
    import json
    p=json.loads(byid[r['id']]['body']['messages'][1]['content']);assert set(p)=={'claim','reference'} and p['claim']==r['text'] and p['reference']==r['reference']
    counts[len(refs)]+=1
c.put(c.OUT/'input_binding_check.json',dict(N=len(rows),all_headers_and_offsets_exact=True,no_GT_payload=True,entry_counts=dict(counts),source_sha256=c.sha(c.PRIVATE/'screen_inputs.jsonl')))
print('All300 reference headers/offsets and constructor field whitelist PASS')
