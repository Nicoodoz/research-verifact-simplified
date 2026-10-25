"""Post-hoc source/batch reporting, not a new method or selected cohort."""
import common078 as c
from analyze078 import metrics,pair
def main():
 rows=c.lines(c.OUT/'predictions.jsonl');groups={}
 for source in ['052','053']:groups['primary_source_'+source]=[x for x in rows if x['source_task']==source]
 for mode in ['reused','new']:groups['F4_'+mode]=[x for x in rows if 'F4' in x['arms'] and x['arms']['F4']['mode']==mode]
 tables={};pairs={}
 for name,rr in groups.items():
  methods=['Original','NS_U2','GateA','NS_StdM','NS_StdV','TS_raw','TS_U2','TS_PriorG']
  if name.startswith('F4'):methods+=['F4_raw','F4_PriorG']
  tables[name]=[metrics(rr,m) for m in methods]
  pp=[('Original','TS_PriorG'),('NS_U2','TS_PriorG')]
  if name.startswith('F4'):pp+=[('TS_raw','F4_raw'),('TS_PriorG','F4_PriorG')]
  pairs[name]=[pair(rr,b,a) for b,a in pp]
  print(c.canon(dict(group=name,n=len(rr),points=[dict(method=v['method'],correct=v['correct'],MCC=v['MCC'],falseS=v['falseS']) for v in tables[name]])))
 peers=c.lines(c.OUT/'gate_peers.jsonl');blind={x['id']:x for x in c.lines(c.OUT/'primary_blind.jsonl')}
 for q in peers:
  payload=c.json.loads(q['body']['messages'][-1]['content']);x=blind[q['id']];assert payload==dict(proposition=x['claim'],reference=x['reference'])
 c.put(c.OUT/'source_batch_supplement.json',dict(created_utc=c.now(),role='post-hoc descriptive source/batch sensitivity; all groups retained; no new method',tables=tables,paired=pairs,gate_peer_exact_claim_reference_checks=len(peers)))
if __name__=='__main__':main()
