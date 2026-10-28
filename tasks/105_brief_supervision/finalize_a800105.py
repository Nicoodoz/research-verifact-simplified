"""Offline final artifacts from completed frozen105 replies; no model calls."""
from pathlib import Path
from collections import Counter
import json,shutil,statistics,argparse,re
import common105 as c
from parse105 import parse

def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args()
 keys=c.rows(c.OUT/'eval_keys.jsonl');keymap={r['id']:r for r in keys};inputs={r['id']:r for r in c.rows(c.PRIVATE/'eval_inputs.jsonl')}
 all_records={};public=[];resources={};format_counts={}
 for arm in c.ARMS:
  data={};batches=[];fmt=Counter();quotes=Counter()
  for file in sorted((a.results/'eval'/arm).glob('batch-*.json')):
   if '.inflight.' in file.name:continue
   saved=c.read(file);batches.append(saved)
   for r in saved['records']:
    assert r['id'] not in data;data[r['id']]=r;parsed=parse(r['content'],r['finish_reason']);assert parsed==r['parsed']
    fmt['N']+=1;fmt['valid']+=parsed['valid'];fmt['strict_json']+=parsed['strict_json'];fmt['length_finish']+=r['finish_reason']=='length';fmt['exact_label_normalized']+=parsed['exact_label_normalized']
    fenced=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',r['content'],re.S|re.I)
    try:obj=json.loads(fenced[1] if fenced else r['content'].strip()) if parsed['valid'] else {}
    except (ValueError,TypeError):obj={}
    if not isinstance(obj,dict):obj={}
    evidence=obj.get('evidence');relation=obj.get('relation');reason=obj.get('reason')
    fmt['nonempty_relation']+=isinstance(relation,str) and bool(relation.strip());fmt['nonempty_reason']+=isinstance(reason,str) and bool(reason.strip())
    if isinstance(evidence,list):
     fmt['evidence_list']+=1;fmt['empty_evidence_list']+=not evidence
     for quote in evidence:
      quotes['quotes']+=1;quotes['literal_in_same_reference']+=isinstance(quote,str) and bool(quote) and quote in inputs[r['id']]['reference']
    public.append({k:r[k] for k in ['id','arm','prompt_token_sha256','input_tokens','output_tokens','finish_reason','parsed']})
  assert set(data)==set(keymap),'Finalization requires all500 physical replies, including invalids'
  all_records[arm]=data;seconds=sum(b['batch_seconds'] for b in batches);tokens=sum(r['output_tokens'] for r in data.values())
  resources[arm]=dict(N=len(data),batch_count=len(batches),generation_seconds=seconds,output_tokens=tokens,mean_output_tokens=tokens/len(data),max_output_tokens=max(r['output_tokens'] for r in data.values()),aggregate_generation_tokens_per_second=tokens/seconds,peak_allocated_bytes=max(b['peak_allocated_bytes'] for b in batches),interpretation='Aggregate includes prefill and generated answer; not isolated decoding speed')
  format_counts[arm]=dict(fmt,**quotes)
 for i in keymap:assert len({all_records[arm][i]['prompt_token_sha256'] for arm in c.ARMS})==1
 transitions=[];pairs={}
 for pan in ['natural','pressure']:
  for base,new in [('label_only','evidence_brief'),('base_judge','evidence_brief'),('base_judge','label_only')]:
   rows=[];patient=Counter();bygt={g:Counter() for g in c.LABELS}
   for k in keys:
    if k['panel']!=pan or not all(all_records[arm][k['id']]['parsed']['valid'] for arm in c.ARMS):continue
    before=all_records[base][k['id']]['parsed']['verdict'];after=all_records[new][k['id']]['parsed']['verdict'];gt=k['GT']
    rescue=before!=gt and after==gt;harm=before==gt and after!=gt;patient[str(k['sid'])]+=int(rescue)-int(harm)
    row=dict(id=k['id'],sid=k['sid'],author=k['author'],panel=pan,GT=gt,baseline=base,candidate=new,before=before,after=after,rescue=rescue,harm=harm,false_S_added=gt!='Supported' and before!='Supported' and after=='Supported',false_S_prevented=gt!='Supported' and before=='Supported' and after!='Supported')
    rows.append(row);bygt[gt]['rescue']+=rescue;bygt[gt]['harm']+=harm
    if before!=after:transitions.append(row)
   pairs[pan+'/'+new+'__vs__'+base]=dict(N=len(rows),rescue=sum(r['rescue'] for r in rows),harm=sum(r['harm'] for r in rows),by_GT={g:dict(v) for g,v in bygt.items()},patient_net=dict(patient),patient_win_loss_tie=[sum(x>0 for x in patient.values()),sum(x<0 for x in patient.values()),sum(x==0 for x in patient.values())],false_S_added=sum(r['false_S_added'] for r in rows),false_S_prevented=sum(r['false_S_prevented'] for r in rows))
 training={}
 for arm in c.ARMS[1:]:
  root=a.results/'train'/arm;done=c.read(root/'training_done.json');assert done['step']==50 and done['consumed']==392
  steps=c.rows(root/'steps.jsonl');assert len(steps)==50 and sum(r['microbatches'] for r in steps)==392
  expected=c.read(c.OUT/'training_plan.json')
  # Full order is checked against the duplicated original196 IDs, independently of labels.
  frozen=c.rows(c.PRIVATE/'train'/f'{arm}.jsonl');assert [i for s in steps for i in s['ids']]==[r['id'] for r in frozen]*2
  steady=steps[1:];training[arm]=dict(done=done,steps=50,consumed=392,step_wall_seconds=sum(s['seconds'] for s in steps),checkpoint_seconds=sum(s['checkpoint_seconds'] for s in steps),steady_tokens_per_second=sum(s['tokens'] for s in steady)/sum(s['seconds'] for s in steady),peak_allocated_bytes=max(s['peak_allocated_bytes'] for s in steps))
  for name in ['steps.jsonl','training_done.json','adapter_setup.json','resume.json']:
   dst=c.OUT/'a800_resources'/arm/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,dst)
 c.putl(c.OUT/'predictions_sanitized.jsonl',public);c.putl(c.OUT/'paired_transitions.jsonl',transitions)
 c.put(c.OUT/'paired_transition_summary.json',pairs);c.put(c.OUT/'output_quality.json',dict(mechanical_only_not_semantic_validation=True,arms=format_counts))
 c.put(c.OUT/'a800_resources.json',dict(training=training,evaluation=resources,all_inputs_equal=True,all1500_received=True,training_order_equal=True))
 print(c.canonical(dict(all1500_received=True,training_order_equal=True,format=format_counts)))

if __name__=='__main__':main()
