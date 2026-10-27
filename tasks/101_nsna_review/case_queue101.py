"""Fixed hash representative changed cases, private text; no new inference or GT modification."""
import json
from collections import defaultdict
import common101 as c,runtime101 as rt
def main():
 a=c.read(c.OUT/'analysis.json');rows={r['id']:r for r in c.lines(c.OUT/'predictions.jsonl')};materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')}
 jobs={(j['id'],j['arm']):j for j in c.lines(c.PRIVATE/'confirmation_jobs.jsonl') if not j['repeat']};done=rt.completed();bindings=c.read(c.OUT/'baseline_bindings.json');selected={}
 for arm in c.REVIEW_ARMS:
  groups=defaultdict(list)
  for x in a['paired']['natural'][arm+'__vs__verifact_ref']['changes']:
   if x['kind'] in ['rescue','harm']:groups[x['kind'],x['GT']].append(x)
  for key,xx in groups.items():
   for x in sorted(xx,key=lambda x:c.digest('101/caseaudit/v1/'+x['id']))[:2]:selected[x['id']]=rows[x['id']]
 records=[]
 for pid,r in selected.items():
  b=bindings[pid];tr=c.read(c.ROOT/b['receipt_path'])['transport'];base=json.loads(tr['body_text'])['choices'][0]['message']['content'];out={}
  for arm in c.REVIEW_ARMS:
   j=jobs[pid,arm];tr=c.read(done[j['request_id']]/'receipt.json')['transport'];out[arm]=json.loads(tr['body_text'])['choices'][0]['message']['content']
  records.append(dict(id=pid,sid=r['sid'],GT=r['GT'],predictions=r['predictions'],claim=materials[pid]['claim'],reference=materials[pid]['reference'],baseline_output=base,review_outputs=out))
 c.putl(c.PRIVATE/'case_review_queue.jsonl',records)
 c.put(c.OUT/'case_review_selection.json',dict(rule='Up to two hash-smallest IDs per arm/rescue-or-harm/GT cell on natural confirmation; overlap shared; descriptive source reading only',IDs=list(selected),N=len(selected),no_new_GT=True))
 print(c.canonical(dict(N=len(records),IDs=list(selected))))
if __name__=='__main__':main()
