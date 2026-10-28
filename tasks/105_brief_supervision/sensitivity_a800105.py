"""Offline pair-only coverage sensitivity, never replacement of frozen main analysis."""
import common105 as c
from evaluate105 import metric,cohort,preds,risk_deltas,paired_compare
from collections import Counter

def main():
 keys=c.rows(c.OUT/'eval_keys.jsonl');records=c.rows(c.OUT/'predictions_sanitized.jsonl');index={(r['arm'],r['id']):r for r in records};result={}
 for panel in ['natural','pressure']:
  rows=[]
  for k in keys:
   if k['panel']==panel and all(index[a,k['id']]['parsed']['valid'] for a in ['label_only','evidence_brief']):rows.append(dict(k,pred={a:index[a,k['id']]['parsed']['verdict'] for a in ['label_only','evidence_brief']}))
  result[panel]=dict(N=len(rows),GT=dict(Counter(r['GT'] for r in rows)),metrics={a:metric(rows,a) for a in ['label_only','evidence_brief']},paired=paired_compare(cohort(rows),preds(rows,'label_only'),preds(rows,'evidence_brief')),risk=risk_deltas(rows,'label_only','evidence_brief'))
 c.put(c.OUT/'pair_only_sensitivity.json',dict(purpose='Remove third-arm format exclusions as an offline sensitivity; frozen main common-three analysis unchanged',panels=result))
 print(c.canonical({k:dict(N=v['N'],MCC_delta=v['paired']['metrics']['mcc']) for k,v in result.items()}))

if __name__=='__main__':main()
