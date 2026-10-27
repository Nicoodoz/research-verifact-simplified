"""Post-primary offline sensitivity: exact entire label only, never text search/GT repair."""
import sys,json,itertools
import common103 as c
import runtime103 as rt
from parse103 import parse
sys.path.insert(0,str(c.ROOT/'tasks/099_judge_selection'))
from analyze099 import panel
def main():
 primary=c.read(c.OUT/'analysis.json');preds={r['id']:r for r in c.lines(c.OUT/'predictions.jsonl') if r['direct48']};done=rt.completed();changes=[]
 for j in c.lines(c.PRIVATE/'jobs_label_capacity.jsonl'):
  tr=c.read(done[j['request_id']]/'receipt.json')['transport'];content=json.loads(tr['body_text'])['choices'][0]['message']['content'];p=parse(tr)
  if not p['valid'] and content.strip() in c.LABELS:
   literal=content.strip();preds[j['id']]['predictions'][j['model']+'__label']=literal;preds[j['id']]['arms'][j['model']+'__label']=dict(valid=True,verdict=literal,exact_label_normalized=True,format_anomaly=True)
   changes.append(dict(id=j['id'],model=j['model'],whole_output=literal,response_text_sha256=c.digest(content),no_GT_used_in_normalization=True))
 results=panel(list(preds.values()),[m+'__label' for m in c.MODELS]);reversal=[]
 for a,b in itertools.combinations(c.MODELS,2):
  na=primary['native_same48']['tables'][a+'__native'];nb=primary['native_same48']['tables'][b+'__native'];la=results['tables'][a+'__label'];lb=results['tables'][b+'__label']
  if (na['mcc']-nb['mcc'])*(la['mcc']-lb['mcc'])<0 and (abs(la['mcc']-lb['mcc'])>=.05 or abs(la['correct']-lb['correct'])>=3):reversal.append(dict(a=a,b=b,native_mcc_delta=na['mcc']-nb['mcc'],label_mcc_delta=la['mcc']-lb['mcc']))
 c.put(c.OUT/'label_format_sensitivity.json',dict(utc=c.utc(),after_primary_analysis=True,primary_preserved=True,normalizations=changes,results=results,material_mode_reversals_same48=reversal,GPU_parser_frozen_before_GPU_predictions=True))
 print(c.canonical({m:dict(mcc=t['mcc'],correct=t['correct'],false_S=t['false_S'],recall={k:v['recall'] for k,v in t['per_class'].items()}) for m,t in results['tables'].items()}))
if __name__=='__main__':main()
