"""Read-only reconstruction of existing runs; no transport clients or model fitting."""
import argparse,csv,datetime,hashlib,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/076_existing_results_synthesis';TASK=Path(__file__).parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tasks/053_thinking_prior_validation'))
import common053 as c53
from verifact_research.evaluation import evaluate,paired_compare
LABELS=c53.LABELS;SOURCE_HASHES={}
DIRS={71:'071_judge_icl_feasibility',72:'072_adaptive_judge_examples',73:'073_clinical_example_matching',74:'074_anchor_dynamic_examples',75:'075_annotated_static_examples'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def touch(p):
 p=Path(p);SOURCE_HASHES[p.relative_to(ROOT).as_posix()]=sha(p);return p
def read(p):return json.loads(touch(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in touch(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def put(name,x):
 with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def jl(name,rows):
 with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:
  for x in rows:f.write(canon(x)+'\n')
def cohort(rows):return [dict(proposition_id=x['id'],subject_id=x['sid'],human_gt=x['GT']) for x in rows]
def preds(rows,field):return [dict(proposition_id=x['id'],verdict=x[field]) for x in rows]
def metric(rows,field,bootstrap=False):
 e=evaluate(cohort(rows),preds(rows,field),profile='research_patient' if bootstrap else 'none',missing='error',iterations=1000)
 return dict(n=len(rows),patients=len({x['sid'] for x in rows}),correct=sum(x[field]==x['GT'] for x in rows),PA=e['percent_agreement'],MCC=e['mcc'],AC1=e['gwet_ac1'],falseS=sum(x['GT']!='Supported' and x[field]=='Supported' for x in rows),confusion=e['confusion_matrix'],recall={k:e['per_class'][k]['recall'] for k in LABELS},coverage=e['coverage'],ci=e.get('confidence_intervals'))
def compare(rows,before,after,bootstrap=True):
 z=dict(n=len(rows),rescue=sum(x[before]!=x['GT'] and x[after]==x['GT'] for x in rows),harm=sum(x[before]==x['GT'] and x[after]!=x['GT'] for x in rows))
 z['net']=z['rescue']-z['harm'];z['delta_falseS']=sum(x['GT']!='Supported' and x[after]=='Supported' for x in rows)-sum(x['GT']!='Supported' and x[before]=='Supported' for x in rows)
 z['patient_net']={sid:sum((x[after]==x['GT'])-(x[before]==x['GT']) for x in rows if x['sid']==sid) for sid in sorted({x['sid'] for x in rows})}
 if bootstrap and len(z['patient_net'])>=2:z['paired']=paired_compare(cohort(rows),preds(rows,before),preds(rows,after),iterations=1000)
 return z
def stage_sources(task,stage):
 d=ROOT/'outputs'/DIRS[task]
 if task==71:return d/'evaluation_blind.jsonl',d/'evaluation_gt.jsonl',d/'stage1_predictions.jsonl',d/'main_jobs.jsonl',d/'stage1_analysis.json'
 jobs=d/(stage+'_jobs.jsonl' if task==72 else stage+'_aliases.jsonl')
 return d/'target_blind.jsonl',d/'target_gt.jsonl',d/(stage+'_predictions.jsonl'),jobs,d/(stage+'_analysis.json')
def native_index(task):
 out={};counts=Counter()
 for p in sorted((ROOT/'outputs'/DIRS[task]/'attempts').glob('*/request.json')):
  rq=read(p);rp=p.parent/'receipt.json'
  if not rp.exists():counts['missing_receipt']+=1;continue
  rc=read(rp);assert rc['request_sha256']==sha(p)
  tr=rc['transport'];counts[str(tr['http_status'])]+=1
  if tr['http_status']!=200:continue
  j=rq['job'];rid=j['request_id'];assert rid not in out
  out[rid]=dict(job=j,transport=tr,parsed=c53.parse_response(tr,True,True),request=p.relative_to(ROOT).as_posix(),receipt=rp.relative_to(ROOT).as_posix())
 return out,dict(counts)
def decode_scores(scores,frozen):
 logits=c53.log_scores(scores);g=c53.calibrated(scores,frozen['calibration_theta']['T-S']['G'],'G')
 prior=c53.prior_adjust(logits,frozen['reference_prior_counts'],frozen['calibration_counts']['T-S'])
 full=c53.prior_adjust(g,frozen['reference_prior_counts'],frozen['calibration_counts']['T-S'])
 return dict(score_argmax=c53.decode_logits(logits),G_only=c53.decode_logits(g),prior_only=c53.decode_logits(prior),PriorG=c53.decode_logits(full))
def pair_rows(rows,base,arm):
 a={x['id']:x for x in rows if x['arm']==arm};b={x['id']:x for x in rows if x['arm']==base};assert a.keys()==b.keys()
 return [dict(id=i,sid=a[i]['sid'],author=a[i]['author'],GT=a[i]['GT'],base=b[i],candidate=a[i],braw=b[i]['raw'],craw=a[i]['raw'],barg=b[i]['score_argmax'],carg=a[i]['score_argmax'],bfinal=b[i]['PriorG'],cfinal=a[i]['PriorG'],both_valid=b[i]['valid'] and a[i]['valid'],same_body=b[i]['body_sha256']==a[i]['body_sha256']) for i in sorted(a)]
def decompose(rows,base,arm):
 p=pair_rows(rows,base,arm);v=[x for x in p if x['both_valid']];excluded=[x for x in p if not x['both_valid']]
 full=compare(p,'bfinal','cfinal');raw=compare(v,'braw','craw');final=compare(v,'bfinal','cfinal')
 effects={side:sum((x[side+'final']==x['GT'])-(x[side+'raw']==x['GT']) for x in v) for side in ['b','c']}
 arg_effect={side:sum((x[side+'arg']==x['GT'])-(x[side+'raw']==x['GT']) for x in v) for side in ['b','c']}
 exnet=sum((x['cfinal']==x['GT'])-(x['bfinal']==x['GT']) for x in excluded)
 assert final['net']==raw['net']+effects['c']-effects['b'];assert full['net']==final['net']+exnet
 same=[x for x in p if x['same_body']];different=[x for x in p if not x['same_body']]
 # A changed raw label and a correct final label are two separate observations.
 final_rescues=[x for x in v if x['bfinal']!=x['GT'] and x['cfinal']==x['GT']]
 classes={label:dict(n=sum(x['GT']==label for x in v),raw_net=sum((x['craw']==x['GT'])-(x['braw']==x['GT']) for x in v if x['GT']==label),final_net=sum((x['cfinal']==x['GT'])-(x['bfinal']==x['GT']) for x in v if x['GT']==label)) for label in LABELS}
 authors={author:dict(n=sum(x['author']==author for x in v),raw_net=sum((x['craw']==x['GT'])-(x['braw']==x['GT']) for x in v if x['author']==author),final_net=sum((x['cfinal']==x['GT'])-(x['bfinal']==x['GT']) for x in v if x['author']==author)) for author in sorted({x['author'] for x in v})}
 return dict(base=base,candidate=arm,n=len(p),common_valid_n=len(v),excluded_ids=[x['id'] for x in excluded],full_final=full,raw_common=raw,final_common=final,base_post_net=effects['b'],candidate_post_net=effects['c'],differential_post_net=effects['c']-effects['b'],differential_argmax_vs_verdict_net=arg_effect['c']-arg_effect['b'],differential_fixed_score_transform_net=(effects['c']-arg_effect['c'])-(effects['b']-arg_effect['b']),fallback_involved_net=exnet,same_body_n=len(same),same_body_final_net=sum((x['cfinal']==x['GT'])-(x['bfinal']==x['GT']) for x in same),changed_body_n=len(different),changed_body_final_net=sum((x['cfinal']==x['GT'])-(x['bfinal']==x['GT']) for x in different),final_rescues_common=len(final_rescues),final_rescues_raw_also_correct=sum(x['craw']==x['GT'] for x in final_rescues),final_rescues_raw_still_wrong=sum(x['craw']!=x['GT'] for x in final_rescues),by_gt=classes,by_author=authors)
def main():
 OUT.mkdir(exist_ok=False)
 frozen=read(ROOT/'outputs/053_thinking_prior_validation/freeze.json')
 prior=frozen['reference_prior_counts'];cal=frozen['calibration_counts']['T-S'];theta=frozen['calibration_theta']['T-S']['G'][0]
 factors={k:(prior[k]/sum(prior.values()))/(cal[k]/sum(cal.values()))*math.exp(theta if k=='Supported' else 0) for k in LABELS}
 put('fixed_transform.json',dict(reference_counts=prior,calibration_counts=cal,G_log_shift=theta,weights=factors,weights_relative_to_NS={k:v/factors['Not Supported'] for k,v in factors.items()},tie_order=['Not Supported','Not Addressed','Supported'],zero_score_probability_floor=1e-6,new_fits=0))
 meta={x['proposition_id']:x for x in csv.DictReader(touch(ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig'))}
 fallback53={x['id']:x['U2'] for x in csv.DictReader(touch(ROOT/'outputs/053_thinking_prior_validation/predictions.csv').open(encoding='utf-8-sig'))}
 fallback34={x['proposition_id']:x['U2'] for x in csv.DictReader(touch(ROOT/'outputs/034_same_data_comparison/predictions_common.csv').open(encoding='utf-8-sig'))}
 stages=[(71,'stage1'),(72,'pilot'),(72,'confirmation'),(73,'pilot'),(73,'confirmation'),(74,'pilot'),(75,'pilot')]
 native={};native_counts={};records=[];cohorts={};summary={};pairs={};post=[];checks=0
 for task,stage in stages:
  key=f'{task:03}_{stage}'
  if task not in native:native[task],native_counts[str(task)]=native_index(task)
  bf,gf,pf,jf,af=stage_sources(task,stage);blind={x['id']:x for x in lines(bf)};gold={x['id']:x for x in lines(gf)};historical=read(af)
  predictions=lines(pf);jobs={(j['id'],j['arm']):j for j in lines(jf)};new=[]
  for p in predictions:
   pid=p['id'];t=blind[pid];gt=gold[pid]['GT'];j=jobs[pid,p['arm']];answer_id=p.get('recovered_by_request_id') or p['request_id'];rec=native[task][answer_id];z=rec['parsed']
   assert canon(rec['job']['body'])==canon(j['body']);assert digest(j['body'])==j['body_sha256'];assert z.get('model_returned')=='deepseek-v4-flash-0731';checks+=3
   assert json.loads(j['body']['messages'][-1]['content'])==dict(proposition=t['claim'],reference=t['reference']);assert gt==meta[pid]['human_gt'] and t['sid']==meta[pid]['subject_id'] and t['author']==meta[pid]['author_type'];checks+=2
   valid=z['status'] in c53.VALID and z.get('scores') is not None
   raw=z.get('verdict') if z['status'] in c53.VALID and z.get('verdict') in LABELS else None
   assert p['scores']==z.get('scores') and p['raw']==raw and p['fallback']==(not valid);checks+=1
   dec=decode_scores(z['scores'],frozen) if valid else dict(score_argmax=None,G_only=None,prior_only=None,PriorG=(fallback53 if task in (71,72) else fallback34)[pid])
   assert dec['PriorG']==p['PriorG'];checks+=1
   arm='F4' if task==71 and p['arm']=='E' else ('C4' if task==71 and p['arm']=='C' else p['arm'])
   row=dict(stage=key,task=task,phase=stage,id=pid,sid=t['sid'],author=t['author'],GT=gt,arm=arm,source_arm=p['arm'],raw=raw,scores=z.get('scores'),valid=valid,fallback=not valid,**dec,request_id=j['request_id'],answer_request_id=answer_id,body_sha256=digest(j['body']),reference_sha256=hashlib.sha256(t['reference'].encode()).hexdigest(),system_sha256=hashlib.sha256(j['body']['messages'][0]['content'].encode()).hexdigest(),request_source=rec['request'],receipt_source=rec['receipt'],prediction_source=pf.relative_to(ROOT).as_posix(),usage=z.get('usage'),parsed_status=z['status'])
   records.append(row);new.append(row)
  ids=sorted({x['id'] for x in new});arms=sorted({x['arm'] for x in new});common=[i for i in ids if all(next(x for x in new if x['id']==i and x['arm']==arm)['valid'] for arm in arms)]
  cohorts[key]=dict(n=len(ids),patients=sorted({x['sid'] for x in new}),ids=ids,GT_counts=dict(Counter(gold[i]['GT'] for i in ids)),author_GT_counts=dict(Counter(blind[i]['author']+'/'+gold[i]['GT'] for i in ids)),shared_all_arms_core_valid_n=len(common),input_reference_equal_across_arms=all(len({x['reference_sha256'] for x in new if x['id']==i})==1 for i in ids))
  summary[key]={}
  for arm in arms:
   rr=[x for x in new if x['arm']==arm];vv=[x for x in rr if x['valid']];cc=[x for x in rr if x['id'] in common]
   final=metric(rr,'PriorG');raw_common=metric(cc,'raw');oldarm=rr[0]['source_arm']
   for name,actual in [('final_metrics',final),('raw_metrics',raw_common)]:
    expected=historical[name][oldarm];assert actual['correct']==expected['correct'] and actual['falseS']==expected['falseS'] and abs(actual['MCC']-expected['MCC'])<1e-12;checks+=1
   summary[key][arm]=dict(full_final=final,raw_all_arms_common=raw_common,invalid_ids=[x['id'] for x in rr if not x['valid']],mean_prompt_tokens=sum(x['usage']['prompt_tokens'] for x in rr)/len(rr),mean_completion_tokens=sum(x['usage']['completion_tokens'] for x in rr)/len(rr))
   ablation={field:metric(vv,field) for field in ['raw','score_argmax','G_only','prior_only','PriorG']}
   movement=compare(vv,'raw','PriorG',False);raw_arg_disagree=[x['id'] for x in vv if x['raw']!=x['score_argmax']]
   post.append(dict(stage=key,arm=arm,n=len(vv),ablation=ablation,raw_to_final=movement,raw_argmax_disagreement_ids=raw_arg_disagree,score_transform_transitions=dict(Counter(x['score_argmax']+' -> '+x['PriorG'] for x in vv)),author_effect={author:compare([x for x in vv if x['author']==author],'raw','PriorG',False) for author in sorted({x['author'] for x in vv})},prior_only_vs_full_changed_ids=[x['id'] for x in vv if x['prior_only']!=x['PriorG']]))
  pairs[key]={}
  requests=[('B',a) for a in arms if a!='B']+[('F4',a) for a in arms if a not in ['B','F4']]
  if task==71:requests.append(('C4','F4'))
  if task==73 and stage=='pilot':requests += [('D4','L4'),('D4','M4'),('L4','M4')]
  if task==74:requests.append(('F6','H6'))
  for b,a in requests:pairs[key][a+'_minus_'+b]=decompose(new,b,a)
  print(canon(dict(stage=key,n=len(ids),arms=arms,receipt_prediction_checks=checks)),flush=True)
 jl('unified_predictions.jsonl',records);put('stage_cohorts.json',cohorts);put('stage_results.json',summary);put('paired_decomposition.json',pairs);put('fixed_postprocessing_ablation.json',post);put('receipt_index_counts.json',native_counts)
 # Explicitly de-duplicate fixed F4/B across repeated 071/072 cases, never by correctness.
 eligible={};overlaps={a:{b:len(set(x['ids'])&set(y['ids'])) for b,y in cohorts.items()} for a,x in cohorts.items()}
 for key in cohorts:
  rr=[x for x in records if x['stage']==key]
  for p in pair_rows(rr,'B','F4'):eligible.setdefault(p['id'],[]).append((key,p))
 pooled={};chosen_rows=[]
 for policy,index in [('earliest',0),('latest',-1)]:
  selected=[]
  for pid,options in eligible.items():
   options.sort(key=lambda x:x[0]);key,p=options[index]
   if len(options)>1:
    assert len({o[1]['base']['body_sha256'] for o in options})==1 and len({o[1]['candidate']['body_sha256'] for o in options})==1;checks+=1
   selected += [p['base'],p['candidate']];chosen_rows.append(dict(policy=policy,id=pid,stage=key,alternatives=[z[0] for z in options]))
  pooled[policy]=decompose(selected,'B','F4')
  pooled[policy]['metrics_full']={arm:metric([x for x in selected if x['arm']==arm],'PriorG',True) for arm in ['B','F4']}
  commonids={x['id'] for x in pair_rows(selected,'B','F4') if x['both_valid']}
  pooled[policy]['metrics_raw_common']={arm:metric([x for x in selected if x['arm']==arm and x['id'] in commonids],'raw',True) for arm in ['B','F4']}
  pooled[policy]['unique_patients']=len({x['sid'] for x in selected})
 put('stage_overlap.json',overlaps);put('static_F4_deduplicated.json',pooled);jl('static_pool_selection.jsonl',chosen_rows)
 # Original vs repeat in 068 v2: keep diagnostic subset and whole cohort separate.
 rows=lines(ROOT/'outputs/068_final_pack_utility_diagnosis/forensic_v2_cases.jsonl')
 assert all(x[k] in LABELS for x in rows for k in ['baseline_raw','final_raw','baseline_pg','final_pg'])
 v2=dict(n=len(rows),source_level='stored 068 forensic rows replayed; not a new 067 provenance audit',raw=compare(rows,'baseline_raw','final_raw'),final=compare(rows,'baseline_pg','final_pg'),metrics={k:metric(rows,k) for k in ['baseline_raw','final_raw','baseline_pg','final_pg']})
 v2['base_post_net']=sum((x['baseline_pg']==x['GT'])-(x['baseline_raw']==x['GT']) for x in rows);v2['candidate_post_net']=sum((x['final_pg']==x['GT'])-(x['final_raw']==x['GT']) for x in rows)
 repeat=lines(ROOT/'outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl')
 v2['repeat_subset']=dict(n=len(repeat),raw=compare(repeat,'old_repeat_raw','v2_repeat_raw'),final=compare(repeat,'old_repeat_pg','v2_repeat_pg'),stable_original_final_rescues=sum(x['old_original_pg']!=x['GT'] and x['v2_original_pg']==x['GT'] and x['old_repeat_pg']!=x['GT'] and x['v2_repeat_pg']==x['GT'] for x in repeat))
 assert v2['final']['net']==v2['raw']['net']+v2['candidate_post_net']-v2['base_post_net'];put('packing_v2_reconstruction.json',v2)
 # Narrative sources are hashed; no reserved-level data are opened.
 reports=['outputs/036_final_validation/report.md','outputs/036_final_validation/paper_handoff.md','outputs/053_thinking_prior_validation/report.md','outputs/066_oracle_headroom/report.md','outputs/066_oracle_headroom/analysis.json','outputs/067_conservative_evidence_packing/report.md','outputs/068_final_pack_utility_diagnosis/report.md','outputs/069_final_pack_controlled_repair/report.md','outputs/069_final_pack_controlled_repair/067_correction.md','outputs/070_fixed_evidence_reasoning_diagnosis/report.md']+[f'outputs/{d}/report.md' for d in DIRS.values()]
 for rel in reports:touch(ROOT/rel)
 for rel in ['outputs/073_clinical_example_matching/manifest.json','outputs/074_anchor_dynamic_examples/manifest.json','outputs/075_annotated_static_examples/manifest.json']:
  for p,h in read(ROOT/rel)['files'].items():assert sha(ROOT/p)==h,p;checks+=1
 for p,h in SOURCE_HASHES.items():assert sha(ROOT/p)==h,p;checks+=1
 put('verification.json',dict(status='PASS',checks=checks,logical_prediction_rows=len(records),unique_answer_receipts=len({x['receipt_source'] for x in records}),unique_claims=len(eligible),unique_patients=len({x['sid'] for x in records}),stage_sample_occurrences=sum(x['n'] for x in cohorts.values()),new_API_calls=0,new_fits=0,new_parameter_searches=0,source_files=len(SOURCE_HASHES),independent_audit='not performed',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 put('source_manifest.json',SOURCE_HASHES)
 print(canon(dict(status='PASS',rows=len(records),claims=len(eligible),checks=checks,pooled={k:dict(final=v['full_final']['net'],raw=v['raw_common']['net'],common_n=v['common_valid_n'],fallback=v['fallback_involved_net']) for k,v in pooled.items()})))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',help='New output directory, relative to repository; existing directories are never overwritten')
 args=parser.parse_args()
 if args.output:OUT=(ROOT/args.output).resolve()
 main()
