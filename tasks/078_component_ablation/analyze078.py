"""Analyze only after all 078 logical requests have successful HTTP receipts."""
import csv,math,sys
from collections import Counter,defaultdict
import numpy as np
from threadpoolctl import threadpool_limits
import common078 as c
import run078
sys.path.insert(0,str(c.ROOT/'tasks/053_thinking_prior_validation'))
from analyze053 import a_features,gate_prob
sys.path.insert(0,str(c.ROOT/'tasks/022_competition_aware_support_calibration'))
import calibration022 as standard
from verifact_research.evaluation import evaluate,paired_compare
from verifact_research.evaluation.metrics import encode,patient_bootstrap
LABELS=c.c53.LABELS
MAIN=['Original','NV','NS_raw','NS_U2','GateA','NS_StdM','NS_StdV','TV','TS_raw','TS_U2','TS_PriorG']
POST=['NS_raw','NS_U0','NS_U2','NS_G','NS_prior','NS_PriorG','TS_raw','TS_U0','TS_U2','TS_G','TS_prior','TS_PriorG']
NAMES={'Original':'作者原VeriFact（R1-70B）','NV':'C48＋非thinking普通判断','NS_raw':'C48＋非thinking评分，raw','NS_U0':'C48＋非thinking评分，最高分类','NS_U2':'U2：C48＋非thinking评分＋λ2','GateA':'U2＋患者外Gate A','NS_G':'非thinking评分＋冻结G','NS_prior':'非thinking评分＋仅先验修正','NS_PriorG':'非thinking评分＋冻结PriorG','TV':'C48＋thinking普通判断','TS_raw':'C48＋thinking评分，raw','TS_U0':'C48＋thinking评分，最高分类','TS_U2':'C48＋thinking评分＋U2','TS_G':'thinking评分＋冻结G','TS_prior':'thinking评分＋仅先验修正','TS_PriorG':'当前系统：C48＋thinking评分＋PriorG','RN_raw':'作者证据＋非thinking评分，raw','RN_U0':'作者证据＋非thinking评分，最高分类','RN_U2':'作者证据＋非thinking评分＋U2','RN_G':'作者证据＋非thinking评分＋G','RN_prior':'作者证据＋非thinking评分＋仅先验','RN_PriorG':'作者证据＋非thinking评分＋PriorG','RT_raw':'作者证据＋thinking评分，raw','RT_U0':'作者证据＋thinking评分，最高分类','RT_U2':'作者证据＋thinking评分＋U2','RT_G':'作者证据＋thinking评分＋G','RT_prior':'作者证据＋thinking评分＋仅先验','RT_PriorG':'作者证据＋thinking评分＋PriorG','F4_raw':'C48＋thinking评分＋固定四例，raw','F4_U0':'固定四例＋最高分类','F4_U2':'固定四例＋U2','F4_G':'固定四例＋G','F4_prior':'固定四例＋仅先验','F4_PriorG':'C48＋thinking评分＋固定四例＋PriorG'}
NAMES.update(NS_StdM='C48＋非thinking评分＋患者外StdM',NS_StdV='C48＋非thinking评分＋患者外StdV')
CHECKS=0
def cohort(rows):return [dict(proposition_id=x['id'],subject_id=x['sid'],human_gt=x['GT']) for x in rows]
def prediction(rows,method):return [dict(proposition_id=x['id'],verdict=x['methods'][method]['label']) for x in rows]
def metrics(rows,method,ci=False):
 e=evaluate(cohort(rows),prediction(rows,method),profile='research_patient' if ci else 'none',iterations=1000,missing='error')
 costs=[x['methods'][method]['judge_cost_cny'] for x in rows]
 return dict(method=method,name=NAMES[method],n=len(rows),patients=len({x['sid'] for x in rows}),correct=sum(x['methods'][method]['label']==x['GT'] for x in rows),MCC=e['mcc'],PA=e['percent_agreement'],AC1=e['gwet_ac1'],falseS=sum(x['methods'][method]['label']=='Supported' and x['GT']!='Supported' for x in rows),fallback=sum(x['methods'][method]['fallback'] for x in rows),recall={k:e['per_class'][k]['recall'] for k in LABELS},confusion=e['confusion_matrix'],judge_mean_cny=None if any(v is None for v in costs) else float(np.mean(costs)),CI95=e.get('confidence_intervals'),coverage=e['coverage'])
def pair(rows,base,candidate):
 z=paired_compare(cohort(rows),prediction(rows,base),prediction(rows,candidate),iterations=1000)
 rescue=[x['id'] for x in rows if x['methods'][base]['label']!=x['GT'] and x['methods'][candidate]['label']==x['GT']];harm=[x['id'] for x in rows if x['methods'][base]['label']==x['GT'] and x['methods'][candidate]['label']!=x['GT']]
 pat={sid:sum((x['id'] in rescue)-(x['id'] in harm) for x in rows if x['sid']==sid) for sid in sorted({x['sid'] for x in rows})}
 return dict(base=base,candidate=candidate,n=len(rows),patients=len(pat),rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),rescue_ids=rescue,harm_ids=harm,delta_falseS=sum((x['methods'][candidate]['label']=='Supported')-(x['methods'][base]['label']=='Supported') for x in rows if x['GT']!='Supported'),patient_net=pat,metrics=z['metrics'])
def table(rows,methods,ci=False):return [metrics(rows,m,ci) for m in methods]
def main():
 global CHECKS
 run078.verify();attempts,new=run078.state();jobs=c.lines(c.OUT/'main_jobs.jsonl');assert {j['request_id'] for j in jobs}==set(new),'Do not analyze incomplete planned cohort'
 cost=sum(x['cost_cny'] for x in attempts);assert cost<=c.CAP;frozen=c.read(c.OUT/'postprocessing_frozen.json');theta=frozen['calibration_theta'];ref=frozen['reference_prior_counts'];cc=frozen['calibration_counts']
 primary=c.lines(c.OUT/'primary_blind.jsonl');bridgeids={x['id'] for x in c.lines(c.OUT/'bridge_blind.jsonl')};f4ids={x['id'] for x in c.lines(c.OUT/'f4_blind.jsonl')}
 dev=set(c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']['development']);cal=set(c.read(c.ROOT/'outputs/051_thinking_mode_validation/freeze.json')['patient_pool'])
 assert {x['sid'] for x in primary}<=dev and not {x['sid'] for x in primary}&cal
 native={};used_sources={};records=[]
 for r in c.lines(c.OUT/'reused_answers.jsonl'):
  key=r['id'],r['arm'];assert key not in native;native[key]=dict(r,mode='reused');CHECKS+=1
 for answer in new.values():
  j=answer['job'];key=j['id'],j['arm'];assert key not in native;native[key]=dict(id=j['id'],arm=j['arm'],body=j['body'],body_sha256=j['body_sha256'],parsed=answer['parsed'],request_source=answer['request_source'],receipt_source=answer['receipt_source'],mode='new');CHECKS+=1
 expected={(x['id'],x['arm']) for x in c.lines(c.OUT/'aliases.jsonl')};assert set(native)==expected
 # GT joined only here, after prediction closure. It was historically exposed, not a new blind test.
 cmfile=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv';cm={x['proposition_id']:x for x in csv.DictReader(cmfile.open(encoding='utf-8-sig'))};used_sources[cmfile.relative_to(c.ROOT).as_posix()]=c.sha(cmfile)
 originals={};oldpred={}
 for task,folder in [('052','052_first_tier_validation'),('053','053_thinking_prior_validation')]:
  p=c.ROOT/'outputs'/folder/'original_verifact_predictions.jsonl';used_sources[p.relative_to(c.ROOT).as_posix()]=c.sha(p)
  for r in c.lines(p):assert r['id'] not in originals;originals[r['id']]=r['verdict']
  p=c.ROOT/'outputs'/folder/'predictions.csv';used_sources[p.relative_to(c.ROOT).as_posix()]=c.sha(p)
  for r in csv.DictReader(p.open(encoding='utf-8-sig')):oldpred[r['id']]=r
 released=[]
 for author in ['human','llm']:
  p=c.ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv';used_sources[p.relative_to(c.ROOT).as_posix()]=c.sha(p);released+=list(csv.DictReader(p.open(encoding='utf-8-sig')))
 released={x['proposition_id']:x['verdict'] for x in released}
 models=c.read(c.OUT/'gate_models.json');peers={x['id']:x for x in c.lines(c.OUT/'gate_peers.jsonl')};gatediff=[];invalid=[]
 st=c.read(c.OUT/'standard_controls_freeze.json')
 for p,h in st['source_sha256'].items():assert c.sha(c.ROOT/p)==h
 def infer_cost(z,model):
  u=z.get('usage');assert u is not None
  return (int(u['prompt_tokens'])*3+int(u['completion_tokens'])*(12 if model=='qwen3.8-27b' else 9))/1e6
 for x in primary:
  pid=x['id'];m=cm[pid];assert m['subject_id']==x['sid'] and m['author_type']==x['author'] and m['invalid']=='False' and m['proposition_type']=='claim';gt=m['human_gt'];assert gt in LABELS;assert originals[pid]==released[pid]
  r=dict(id=pid,sid=x['sid'],author=x['author'],GT=gt,source_task=x['source_task'],methods={},arms={});methods=r['methods'];ns=native[pid,'NS']['parsed'];assert ns['status'] in c.c53.VALID and ns.get('scores') is not None;fallback=c.c53.decision(ns['scores'],2);basecost=infer_cost(ns,c.MODEL)
  methods['Original']=dict(label=originals[pid],valid=True,fallback=False,judge_cost_cny=None)
  for arm in ['NS','TS','NV','TV']+(['RN','RT'] if pid in bridgeids else [])+(['F4'] if pid in f4ids else []):
   z=native[pid,arm];p=z['parsed'];sc=arm not in ['NV','TV'];valid=p['status'] in c.c53.VALID and (not sc or p.get('scores') is not None);mcost=infer_cost(p,c.MODEL)+(0 if valid else basecost)
   payload=c.read(c.ROOT/z['request_source'])['job']['body'];assert c.digest(payload)==z['body_sha256'];assert c.canon(payload)==c.canon(z['body']);CHECKS+=2
   meta=dict(arm=arm,status=p['status'],valid=valid,raw=p.get('verdict'),scores=p.get('scores'),usage=p['usage'],mode=z['mode'],body_sha256=z['body_sha256'],request_source=z['request_source'],receipt_source=z['receipt_source']);r['arms'][arm]=meta
   if not valid:invalid.append(dict(id=pid,sid=x['sid'],arm=arm,mode=z['mode'],status=p['status'],errors=p.get('errors'),fallback=fallback))
   def store(name,label):methods[name]=dict(label=label,valid=valid,fallback=not valid,judge_cost_cny=mcost,arm=arm)
   if not sc:store(arm,p['verdict'] if valid else fallback);continue
   cond='N-S' if arm in ['NS','RN'] else 'T-S'
   for post in ['raw','U0','U2','G','prior','PriorG']:
    label=fallback
    if valid:
     if post=='raw':label=p['verdict']
     elif post=='U0':label=c.c53.decision(p['scores'],0)
     elif post=='U2':label=c.c53.decision(p['scores'],2)
     else:
      logs=c.c53.calibrated(p['scores'],theta[cond]['G'],'G') if post in ['G','PriorG'] else c.c53.log_scores(p['scores'])
      if post in ['prior','PriorG']:logs=c.c53.prior_adjust(logs,ref,cc[cond])
      label=c.c53.decode_logits(logs)
    store(arm+'_'+post,label)
  u0=methods['NS_U0']['label'];u2=methods['NS_U2']['label'];candidate=u0!='Supported' and u2=='Supported';gp=None;gate=u0;gatecost=basecost
  assert x['sid'] not in models[x['sid']]['final_fit']['training_patients']
  if candidate:
   q=peers[pid]['parsed'];assert q['status'] in c.c53.VALID and q.get('scores') is not None;gp=gate_prob(models[x['sid']],a_features(ns['scores'],q['scores']));gate='Supported' if gp>=models[x['sid']]['threshold'] else u0;gatecost+=infer_cost(q,'qwen3.8-27b')
  methods['GateA']=dict(label=gate,valid=True,fallback=False,judge_cost_cny=gatecost,arm='NS',gate_candidate=candidate,gate_probability=gp)
  sm=st['mapping'][x['sid']];assert x['sid'] not in sm['training_patients']
  for kind in ['M','V']:
   zz=standard.scores_to_z([ns['scores']]);lab=LABELS[int(standard.labels(standard.transform(zz,kind,sm[kind]['theta']))[0])]
   methods['NS_Std'+kind]=dict(label=lab,valid=True,fallback=False,judge_cost_cny=basecost,arm='NS',calibration_fold=sm['fold'])
  old=oldpred[pid];assert old['U2']==u2
  if x['source_task']=='052':assert old['GateA_patient_out']==gate
  else:
   assert old['TS_PriorG']==methods['TS_PriorG']['label'];gatediff.append(dict(id=pid,sid=x['sid'],old_all40=old['GateA'],new_patient_out=gate,GT=gt,changed=old['GateA']!=gate))
  records.append(r);CHECKS+=4
 c.jl(c.OUT/'predictions.jsonl',records);c.put(c.OUT/'GT_join.json',dict(created_utc=c.now(),prediction_HTTP200_complete=True,source_files=used_sources,GT_counts=dict(Counter(r['GT'] for r in records)),authors=dict(Counter(r['author'] for r in records)),GT_by_author={a:dict(Counter(r['GT'] for r in records if r['author']==a)) for a in ['human','llm']},quality_flag_counts={k:dict(Counter(cm[r['id']][k] for r in records)) for k in ['initial_agreement','time_metadata_conflict','second_round_anomaly']},patients=sorted({r['sid'] for r in records}),analysis_code_sha256=c.sha(c.TASK/'analyze078.py')));c.put(c.OUT/'invalid_outputs.json',invalid);c.put(c.OUT/'gate_fairness_reconciliation.json',gatediff)
 bridge=[r for r in records if r['id'] in bridgeids];f4=[r for r in records if r['id'] in f4ids]
 cohorts={'primary':records,'bridge':bridge,'F4':f4};tables={};cohort_lists={};comparisons={}
 bridge_methods=['Original','RN_raw','RN_U2','RN_PriorG','RT_raw','RT_U2','RT_PriorG','NS_raw','NS_U2','NS_PriorG','TS_raw','TS_U2','TS_PriorG','GateA','NS_StdM','NS_StdV']
 f4_methods=['Original','NS_U2','GateA','NS_StdM','NS_StdV','TS_raw','TS_U2','TS_PriorG','F4_raw','F4_U2','F4_PriorG']
 planned={'primary':[('Original','TS_PriorG'),('Original','NS_U2'),('Original','GateA'),('NS_U2','GateA'),('NS_raw','TS_raw'),('NS_U2','TS_U2'),('NS_PriorG','TS_PriorG'),('NV','NS_raw'),('TV','TS_raw'),('NV','TV'),('TS_raw','TS_PriorG'),('TS_U2','TS_PriorG'),('TS_G','TS_PriorG'),('TS_prior','TS_PriorG'),('NS_raw','NS_U2'),('NS_U2','TS_PriorG'),('GateA','TS_PriorG')], 'bridge':[('Original','RN_raw'),('Original','RT_PriorG')]+[(old+'_'+post,new+'_'+post) for old,new in [('RN','NS'),('RT','TS'),('RN','RT'),('NS','TS')] for post in ['raw','U2','PriorG']], 'F4': [('Original','F4_PriorG'),('TS_raw','F4_raw'),('TS_U2','F4_U2'),('TS_PriorG','F4_PriorG')]}
 planned['primary'] += [(b,a) for a in ['NS_StdM','NS_StdV'] for b in ['Original','NS_U2','TS_PriorG']]
 for name,rr in cohorts.items():
  methods=MAIN if name=='primary' else bridge_methods if name=='bridge' else f4_methods
  for author in ['all','human','llm']:
   z=rr if author=='all' else [r for r in rr if r['author']==author];key=name+'_'+author;cohort_lists[key]=[r['id'] for r in z];tables[key]=table(z,methods,False);comparisons[key]=[pair(z,b,a) for b,a in planned[name]]
  valid=[r for r in rr if all(r['methods'][m]['valid'] for m in methods)];key=name+'_common_core';cohort_lists[key]=[r['id'] for r in valid];tables[key]=table(valid,methods,False);comparisons[key]=[pair(valid,b,a) for b,a in planned[name]]
  print(c.canon(dict(cohort=name,n=len(rr),common_core=len(valid),tables='complete')),flush=True)
 tables['postprocessing_all']=table(records,POST+['NS_StdM','NS_StdV']);cohort_lists['postprocessing_all']=[r['id'] for r in records]
 # Score-interface and thinking interactions, at the same reference and exact cohort.
 interactions={}
 for post in ['raw','U2','PriorG']:
  mm={a:metrics(bridge,a+'_'+post) for a in ['RN','RT','NS','TS']}
  interactions[post]=dict(n=len(bridge),thinking_PA_on_author_reference=mm['RT']['PA']-mm['RN']['PA'],thinking_PA_on_C48=mm['TS']['PA']-mm['NS']['PA'],difference_of_differences_PA=(mm['TS']['PA']-mm['NS']['PA'])-(mm['RT']['PA']-mm['RN']['PA']),MCC_delta_on_author_reference=mm['RT']['MCC']-mm['RN']['MCC'],MCC_delta_on_C48=mm['TS']['MCC']-mm['NS']['MCC'],interpretation='descriptive interaction; not additive causal attribution of MCC')
 c.put(c.OUT/'tables.json',tables);c.put(c.OUT/'paired_comparisons.json',comparisons);c.put(c.OUT/'cohort_lists.json',cohort_lists);c.put(c.OUT/'interactions.json',interactions)
 ledger=dict(cap_cny=c.CAP,estimated_usage_and_unknown_cny=cost,attempts=len(attempts),logical_new=len(jobs),http_counts=dict(Counter(str(a['http_status']) for a in attempts)),unknown_reservation_cny=sum(a['cost_cny'] for a in attempts if a['http_status'] in [0,None]),by_arm={arm:dict(attempts=sum(a['arm']==arm for a in attempts),cost_cny=sum(a['cost_cny'] for a in attempts if a['arm']==arm)) for arm in sorted({a['arm'] for a in attempts})},reused_answers=len(c.lines(c.OUT/'reused_answers.jsonl')),no_new_charge_for_reuse=True,price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',attempt_ledger=attempts)
 c.put(c.OUT/'cost_ledger.json',ledger);c.put(c.OUT/'verification.json',dict(status='PASS',checks=CHECKS,all_planned_HTTP200=True,source_fingerprints_unchanged=True,original_predictions_match_002=True,primary_prior_calibration_patient_overlap=0,Gate_patient_training_overlap=0,new_fits=0,independent_audit='not performed',cost_cny=cost))
 print(c.canon(dict(status='PASS',checks=CHECKS,cost=cost,primary=tables['primary_all'])))
if __name__=='__main__':
 with threadpool_limits(limits=1):main()
