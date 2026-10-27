"""Complete frozen-panel evaluation, original GT, no API and no selecting repeat answers."""
from collections import Counter
import csv,json,statistics,sys
import numpy as np
from sklearn.metrics import matthews_corrcoef,f1_score,confusion_matrix
import common101 as c,prompts101 as p,runtime101 as rt
from verifact_research.evaluation import evaluate,paired_compare
ARMS=['paper_r1','verifact_ref','nsna_plain','nsna_review','nsna_all_ns','nsna_all_na']
def cohort(rr):return [dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr]
def preds(rr,a):return [dict(proposition_id=r['id'],verdict=r['predictions'][a]) for r in rr]
def metric(rr,a):
 z=evaluate(cohort(rr),preds(rr,a),profile='none');cm=np.asarray(z['confusion_matrix']);fs=int(cm[1:,0].sum());non=int(cm[1:].sum());ns=int(cm[:,0].sum())
 z.update(correct=int(np.trace(cm)),false_S=fs,non_S=non,false_S_rate=fs/non if non else None,predicted_S=ns,predicted_S_fdr=fs/ns if ns else None,Macro_F1=sum(z['per_class'][l]['f1'] or 0 for l in c.LABELS)/3)
 y=[r['GT'] for r in rr];v=[r['predictions'][a] for r in rr]
 assert abs(matthews_corrcoef(y,v)-z['mcc'])<1e-10
 assert confusion_matrix(y,v,labels=c.LABELS).tolist()==cm.tolist()
 assert abs(f1_score(y,v,labels=c.LABELS,average='macro',zero_division=0)-z['Macro_F1'])<1e-10
 return z
def compare(rr,b,a,bootstrap=True):
 rescued=[r for r in rr if r['predictions'][b]!=r['GT'] and r['predictions'][a]==r['GT']];harmed=[r for r in rr if r['predictions'][b]==r['GT'] and r['predictions'][a]!=r['GT']]
 m0,m1=metric(rr,b),metric(rr,a)
 changes=[dict(id=r['id'],sid=r['sid'],GT=r['GT'],base=r['predictions'][b],candidate=r['predictions'][a],kind='rescue' if r in rescued else 'harm' if r in harmed else 'wrong_to_wrong') for r in rr if r['predictions'][b]!=r['predictions'][a]]
 patient={sid:sum(r['sid']==sid for r in rescued)-sum(r['sid']==sid for r in harmed) for sid in sorted({r['sid'] for r in rr})}
 result=dict(base=b,candidate=a,N=len(rr),delta_MCC=m1['mcc']-m0['mcc'],delta_PA=m1['percent_agreement']-m0['percent_agreement'],delta_Macro_F1=m1['Macro_F1']-m0['Macro_F1'],delta_false_S=m1['false_S']-m0['false_S'],rescue=len(rescued),harm=len(harmed),net=len(rescued)-len(harmed),rescue_by_GT=dict(Counter(r['GT'] for r in rescued)),harm_by_GT=dict(Counter(r['GT'] for r in harmed)),patient_net=patient,patient_win_loss_tie=[sum(x>0 for x in patient.values()),sum(x<0 for x in patient.values()),sum(x==0 for x in patient.values())],changes=changes)
 if bootstrap:result['paired']=paired_compare(cohort(rr),preds(rr,b),preds(rr,a),iterations=1000)
 return result
def receipt(binding):return c.read(c.ROOT/binding['receipt_path'])['transport']
def main():
 assert not (c.PRIVATE/'run.lock').exists()
 for name in ['execution_freeze.json','trigger_freeze.json']:
  for rel,h in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 jobs=c.lines(c.PRIVATE/'confirmation_jobs.jsonl');done=rt.completed();assert all(j['request_id'] in done for j in jobs),'No partial confirmation analysis'
 materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};bindings=c.read(c.OUT/'baseline_bindings.json');jobmap={(j['id'],j['arm'],j['repeat']):j for j in jobs}
 rows=[];usage=[];parsed_public=[]
 for row in c.lines(c.OUT/'cohort.jsonl'):
  if row['stage']!='confirmation':continue
  r=dict(row);pid=r['id'];m=materials[pid];binding=bindings[pid];tr=receipt(binding);b=p.parse(tr,'verifact_ref',m['reference']);baseline=b['verdict'];triggered=baseline in c.LABELS[1:]
  r.update(baseline_valid=b['valid'],triggered=triggered,predictions=dict(paper_r1=r['paper_r1'],verifact_ref=baseline),repeat_predictions={},review={})
  u=json.loads(tr['body_text'])['usage'];usage.append(dict(id=pid,arm='verifact_ref',panel=r['panel'],origin=r['origin'],repeat=False,cached_historical=binding['source']!='101_new',input_tokens=u['prompt_tokens'],output_tokens=u['completion_tokens'],seconds=tr.get('elapsed_seconds'),peak_no_cache_cny=(u['prompt_tokens']*3+u['completion_tokens']*9)/1e6))
  for a in c.REVIEW_ARMS:
   r['predictions'][a]=baseline
   if not triggered:continue
   for rep in [False,True]:
    if (pid,a,rep) not in jobmap:continue
    j=jobmap[pid,a,rep];folder=done[j['request_id']];tr=c.read(folder/'receipt.json')['transport'];parsed=p.parse(tr,a,m['reference'])
    parsed.update(id=pid,arm=a,repeat=rep,receipt_sha256=c.sha(folder/'receipt.json'),request_id=j['request_id']);parsed_public.append(parsed)
    result=parsed['verdict'] if parsed['valid'] else baseline
    if rep:r['repeat_predictions'][a]=result
    else:r['predictions'][a]=result;r['review'][a]=dict(valid=parsed['valid'],raw_verdict=parsed.get('raw_verdict'),fallback=not parsed['valid'],errors=parsed.get('errors',[]),quote_locations=parsed.get('quote_locations',[]))
    u=json.loads(tr['body_text'])['usage'];usage.append(dict(id=pid,arm=a,panel=r['panel'],origin=r['origin'],repeat=rep,cached_historical=False,input_tokens=u['prompt_tokens'],output_tokens=u['completion_tokens'],seconds=tr['elapsed_seconds'],peak_no_cache_cny=(u['prompt_tokens']*3+u['completion_tokens']*9)/1e6))
  for a,label in [('nsna_all_ns','Not Supported'),('nsna_all_na','Not Addressed')]:r['predictions'][a]=label if triggered else baseline
  for a in ARMS[2:]:assert (r['predictions'][a]=='Supported')==(baseline=='Supported')
  rows.append(r)
 c.putl(c.OUT/'predictions.jsonl',rows);c.putl(c.OUT/'parsed_reviews.jsonl',parsed_public);c.putl(c.OUT/'usage.jsonl',usage)
 valid=[r for r in rows if r['baseline_valid']];natural=[r for r in valid if r['panel']=='natural'];pressure=[r for r in valid if r['panel']=='pressure']
 groups=dict(natural=natural,pressure=pressure,additional200=[r for r in natural if r['origin']=='additional200'],original400=[r for r in natural if r['origin']=='098_frozen'])
 groups.update({f'natural_{author}':[r for r in natural if r['author']==author] for author in ['human','llm']})
 tables={};paired={};coverage={};sensitivity={}
 for name,rr in groups.items():
  tables[name]={a:metric(rr,a) for a in ARMS}
  pairs=[('verifact_ref',a) for a in c.REVIEW_ARMS]+[('nsna_plain','nsna_review')]
  paired[name]={a+'__vs__'+b:compare(rr,b,a) for b,a in pairs}
  native=[r for r in rr if not r['triggered'] or all(r['review'][a]['valid'] for a in c.REVIEW_ARMS)]
  sensitivity[name]=dict(common_native_N=len(native),tables={a:metric(native,a) for a in ARMS[:4]})
  coverage[name]=dict(valid_N=len(rr),patients=len({r['sid'] for r in rr}),triggered=sum(r['triggered'] for r in rr),fallbacks={a:sum(r['triggered'] and r['review'][a]['fallback'] for r in rr) for a in c.REVIEW_ARMS})
  print(name,len(rr),'complete',flush=True)
 repetitions=[r for r in valid if all(a in r['repeat_predictions'] for a in c.REVIEW_ARMS)];repeatrows=[dict(r,predictions=dict(r['predictions'],**r['repeat_predictions'])) for r in repetitions]
 repetition=dict(N=len(repetitions),panels=dict(Counter(r['panel'] for r in repetitions)),flips={a:sum(r['predictions'][a]!=r['repeat_predictions'][a] for r in repetitions) for a in c.REVIEW_ARMS},first={a:compare(repetitions,'verifact_ref',a) for a in c.REVIEW_ARMS},second={a:compare(repeatrows,'verifact_ref',a) for a in c.REVIEW_ARMS},review_vs_plain_second=compare(repeatrows,'nsna_plain','nsna_review'))
 decision={}
 for a in c.REVIEW_ARMS:
  z=paired['natural'][a+'__vs__verifact_ref'];t=tables['natural'];pt=tables['pressure'];ad=paired['additional200'][a+'__vs__verifact_ref'];rp=repetition['second'][a]
  target=z['delta_MCC']>=.02-1e-12 and z['net']>=8 and z['delta_false_S']==0 and z['net']>0
  guard=all(pt[a]['per_class'][l]['recall']>=pt['verifact_ref']['per_class'][l]['recall']-.1-1e-12 for l in c.LABELS[1:])
  add=ad['net']>=0 and ad['delta_MCC']>=-1e-12;stable=not(rp['net']<0 and rp['delta_MCC']<0);ci=z['paired']['metrics']['mcc']['ci95'][0]>0
  decision[a]=dict(practical_target=target,pressure_guard=guard,additional_direction=add,repeat_guard=stable,MCC_CI_positive=ci,status='确认支持' if target and guard and add and stable and ci else '点值改善未确认' if target else '失败停止')
 z=paired['natural']['nsna_review__vs__nsna_plain'];pt=tables['pressure'];t=tables['natural']
 incremental=z['net']>=3 and z['delta_MCC']>=.01-1e-12 and all(pt['nsna_review']['per_class'][l]['recall']>=pt['nsna_plain']['per_class'][l]['recall']-.1-1e-12 for l in c.LABELS[1:])
 decision['review_increment']=dict(practical_extra=incremental,MCC_CI_positive=z['paired']['metrics']['mcc']['ci95'][0]>0,beats_class_bias=t['nsna_review']['mcc']>max(t[a]['mcc'] for a in ['nsna_all_ns','nsna_all_na']),core_method_supported=incremental and decision['nsna_review']['practical_target'] and t['nsna_review']['mcc']>max(t[a]['mcc'] for a in ['nsna_all_ns','nsna_all_na']))
 analyses=dict(tables=tables,paired=paired,coverage=coverage,strict_native_sensitivity=sensitivity,repetition=repetition,decision=decision,full_N=700,baseline_invalid=[r['id'] for r in rows if not r['baseline_valid']],S_set_unchanged=True,bootstrap='1000 patient clusters; fixed predictions; historical development exposure not covered')
 c.put(c.OUT/'analysis.json',analyses);c.put(c.OUT/'decision.json',decision)
 with (c.OUT/'main_table.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['panel','configuration','N','MCC','PA','correct','false_S','non_S','Macro_F1','NS_recall','NA_recall'])
  for name,tt in tables.items():
   for a,z in tt.items():w.writerow([name,a,z['n'],z['mcc'],z['percent_agreement'],z['correct'],z['false_S'],z['non_S'],z['Macro_F1'],z['per_class']['Not Supported']['recall'],z['per_class']['Not Addressed']['recall']])
 cost={}
 for panel in ['natural','pressure']:
  relevant=[u for u in usage if u['panel']==panel and not u['repeat']];n=sum(r['panel']==panel for r in rows)
  base=[u for u in relevant if u['arm']=='verifact_ref'];cost[panel]={}
  for arm in ['verifact_ref']+list(c.REVIEW_ARMS):
   uu=base+([u for u in relevant if u['arm']==arm] if arm!='verifact_ref' else [])
   cost[panel][arm]=dict(N=n,logical_calls=len(uu),average_calls=len(uu)/n,input_tokens=sum(u['input_tokens'] for u in uu),output_tokens=sum(u['output_tokens'] for u in uu),mean_pipeline_seconds=sum(u['seconds'] or 0 for u in uu)/n,mean_peak_no_cache_cny=sum(u['peak_no_cache_cny'] for u in uu)/n)
 ledger=[];con=rt.db();attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
 for rid,num,arm,charge,status,folder in attempts:
  fp=c.ROOT/folder;req=c.read(fp/'request.json');tr=c.read(fp/'receipt.json')['transport'];amount,basis=rt.account(req['job'],tr,req['reservation_cny']);assert abs(amount-charge)<1e-9
  ledger.append(dict(request_id=rid,attempt=num,arm=arm,status=status,cost_or_reserved_cny=amount,basis=basis,folder=folder,request_sha256=c.sha(fp/'request.json'),receipt_sha256=c.sha(fp/'receipt.json')))
 c.putl(c.OUT/'attempt_ledger.jsonl',ledger);c.put(c.OUT/'cost_ledger.json',dict(**rt.summary(),unknown_or_unverified_cny=sum(x['cost_or_reserved_cny'] for x in ledger if 'reserved' in x['basis']),deployment=cost,new_cost_by_arm={arm:sum(x['cost_or_reserved_cny'] for x in ledger if x['arm']==arm) for arm in ['verifact_ref']+list(c.REVIEW_ARMS)}))
 c.put(c.OUT/'analysis_complete.json',dict(utc=c.utc(),full_confirmation=True,analysis_sha256=c.sha(c.OUT/'analysis.json'),decision=decision))
 print(c.canonical(dict(decision=decision,cost=rt.summary())),flush=True)
if __name__=='__main__':main()
