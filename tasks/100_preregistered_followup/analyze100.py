"""Complete-phase-only raw evaluation and the frozen one-candidate decision."""
from collections import Counter,defaultdict
import argparse,csv,json,statistics,sys
import common100 as c
import runtime100 as rt
import gates100 as g
sys.path.insert(0,str(c.ROOT/'tasks/098_p90_native_confirmation'))
from analyze098 import metric,compare,gate as old_gate
from common098 import parse_native
sys.path.insert(0,str(c.ROOT/'tasks/099_judge_selection'))
from parse099 import parse as qparse

def panel(rows,arms):
 valid=[r for r in rows if all(r['predictions'].get(a) in c.LABELS for a in arms)]
 coverage={a:dict(frozen_N=len(rows),valid=sum(r['predictions'].get(a) in c.LABELS for r in rows),invalid=sum(r['predictions'].get(a) not in c.LABELS for r in rows),known_correct=sum(r['predictions'].get(a)==r['GT'] for r in rows)) for a in arms}
 tables={a:metric(valid,a) for a in ['Original']+arms} if valid else {}
 pairs={a+'__vs__O':compare(valid,'O',a) for a in arms if a!='O'} if len({r['sid'] for r in valid})>=2 else {}
 for base in ['C','S24','Q']:
  if base in arms and len({r['sid'] for r in valid})>=2:
   for a in arms:
    if a not in ['O',base]:pairs[a+'__vs__'+base]=compare(valid,base,a)
 return dict(frozen_N=len(rows),common_N=len(valid),patients=len({r['sid'] for r in valid}),GT=dict(Counter(r['GT'] for r in valid)),tables=tables,paired=pairs,coverage=coverage,
   own_valid_metrics={a:metric([r for r in rows if r['predictions'].get(a) in c.LABELS],a) if any(r['predictions'].get(a) in c.LABELS for r in rows) else None for a in arms},
   by_author={author:{a:metric([r for r in valid if r['author']==author],a) for a in ['Original']+arms} for author in sorted({r['author'] for r in valid})})

def read_phase(mode):
 assert not (c.PRIVATE/'run.lock').exists()
 for file in ['execution_freeze.json','runtime_analysis_freeze.json']:
  for rel,h in c.read(c.OUT/file)['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 jobs,_=rt.phase_jobs(mode);done=rt.completed();assert all(j['request_id'] in done for j in jobs),'Incomplete frozen phase; no partial quality selection'
 public={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')};rows={pid:dict(public[pid],predictions=dict(Original=public[pid]['Original']),repeat_predictions=dict(Original=public[pid]['Original']),arms={},repeat_arms={}) for pid in sorted({j['id'] for j in jobs})}
 aliases=Counter(j['request_id'] for j in jobs);costs=defaultdict(float);ledger=[];usage=[]
 con=rt.db();attempts=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
 for rid,n,model,amount,status,folder in attempts:
  p=c.ROOT/folder;req=c.read(p/'request.json');rp=p/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None;value,basis=rt.account(req['job'],tr,req['reservation_cny']);assert abs(value-amount)<1e-9;costs[rid]+=value
  ledger.append(dict(request_id=rid,attempt=n,model=model,status=status,cost_or_reserved_cny=value,basis=basis,folder=folder,request_sha256=c.sha(p/'request.json'),receipt_sha256=c.sha(rp) if rp.exists() else None))
 for j in jobs:
  p=done[j['request_id']];req=c.read(p/'request.json');rec=c.read(p/'receipt.json');tr=rec['transport'];assert req['job']['body']==j['body'] and rec['request_sha256']==c.sha(p/'request.json')
  parsed=qparse(tr) if j['branch']=='cross_model' else parse_native(tr);r=rows[j['id']];field='repeat_predictions' if j['repeat'] else 'predictions';afield='repeat_arms' if j['repeat'] else 'arms';r[field][j['arm']]=parsed['verdict'];r[afield][j['arm']]=dict(**parsed,request_id=j['request_id'],body_sha256=j['body_sha256'],receipt_sha256=c.sha(p/'receipt.json'))
  x=json.loads(tr['body_text']);u=x['usage']
  import datetime as dt
  start,end=[dt.datetime.fromisoformat(tr[k]) for k in ['started_utc','ended_utc']];cheap=rt.idle(start) and rt.idle(end) and (end-start).total_seconds()<3600;ip,op,_=rt.prices(j['body']['model'],u['prompt_tokens'],cheap)
  usage.append(dict(id=j['id'],stage=j['stage'],panel=j['panel'],arm=j['arm'],repeat=j['repeat'],request_id=j['request_id'],model=j['body']['model'],prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],reasoning_tokens=(u.get('completion_tokens_details') or {}).get('reasoning_tokens'),cached_tokens=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0),elapsed_seconds=tr['elapsed_seconds'],actual_cost_allocated_cny=costs[j['request_id']]/aliases[j['request_id']],no_cache_deployment_cny=(u['prompt_tokens']*ip+u['completion_tokens']*op)/1e6,alias_count=aliases[j['request_id']],finish_reason=x['choices'][0].get('finish_reason')))
 return list(rows.values()),usage,ledger,jobs

def repeats(rows,arms,winner):
 rr=[r for r in rows if r['repeat_subset'] and all(r['predictions'].get(a) in c.LABELS and r['repeat_predictions'].get(a) in c.LABELS for a in arms)]
 ss=[dict(r,predictions=r['repeat_predictions']) for r in rr]
 first={a:metric(rr,a) for a in ['Original']+arms} if rr else {};second={a:metric(ss,a) for a in ['Original']+arms} if rr else {}
 output=dict(frozen_N=sum(r['repeat_subset'] for r in rows),common_N=len(rr),flips={a:sum(r['predictions'][a]!=r['repeat_predictions'][a] for r in rr) for a in arms},first_tables=first,second_tables=second,
  first_pairs={a+'__vs__O':compare(rr,'O',a) for a in arms if a!='O'} if len({r['sid'] for r in rr})>=2 else {},second_pairs={a+'__vs__O':compare(ss,'O',a) for a in arms if a!='O'} if len({r['sid'] for r in rr})>=2 else {})
 if rr:
  dm=second[winner]['mcc']-second['O']['mcc'];fs0=second['O']['false_S_rate'];fs1=second[winner]['false_S_rate']
  output.update(MCC_reversed=dm<-g.EPS,risk_reversed=fs0 is not None and fs1-fs0>g.EPS,second_delta_MCC=dm,second_delta_false_S_rate=fs1-fs0 if fs0 is not None else None)
 else:output.update(MCC_reversed=False,risk_reversed=False,unassessable=True)
 if 'Q' in arms and len({r['sid'] for r in rr})>=2:
  output['first_pairs']['P__vs__Q']=compare(rr,'Q','P');output['second_pairs']['P__vs__Q']=compare(ss,'Q','P')
  output['original098_reversals']={base:output['first_pairs']['P__vs__'+base]['paired']['metrics']['mcc']['delta']>0 and output['first_pairs']['P__vs__'+base]['net']>0 and output['second_pairs']['P__vs__'+base]['paired']['metrics']['mcc']['delta']<0 and output['second_pairs']['P__vs__'+base]['net']<0 for base in ['O','Q']}
 return output

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['development','confirmation','cross_model_confirmation']);mode=p.parse_args().mode
 rows,usage,ledger,jobs=read_phase(mode);arms=sorted({j['arm'] for j in jobs if not j['repeat']},key=lambda a:['O','C','S24','L24','EHR-all','P','Q'].index(a))
 panels={name:panel([r for r in rows if r['panel']==name],arms if mode!='cross_model_confirmation' or name=='natural' else ['O','P']) for name in ['natural','pressure']}
 coststats={a:dict(N=sum(u['arm']==a and not u['repeat'] for u in usage),mean_no_cache_cny=statistics.mean(u['no_cache_deployment_cny'] for u in usage if u['arm']==a and not u['repeat']),mean_actual_allocated_cny=statistics.mean(u['actual_cost_allocated_cny'] for u in usage if u['arm']==a and not u['repeat']),mean_input=statistics.mean(u['prompt_tokens'] for u in usage if u['arm']==a and not u['repeat']),mean_output=statistics.mean(u['completion_tokens'] for u in usage if u['arm']==a and not u['repeat'])) for a in arms}
 result=dict(panels=panels,costs=coststats)
 if mode=='development':
  cov={a:sum(r['predictions'].get(a) in c.LABELS for r in rows)/len(rows) for a in ['S24','L24','EHR-all']};keepers=[a for a in g.ORDER if cov[a]>=.95-g.EPS]
  selection_panels={name:panel([r for r in rows if r['panel']==name],['O']+keepers) for name in ['natural','pressure']};result['selection_panels']=selection_panels
  decision=g.development_select(selection_panels['natural']['tables'],selection_panels['pressure']['tables'],cov,{a:coststats[a]['mean_no_cache_cny'] for a in g.ORDER})
  c.put(c.OUT/'development_decision.json',decision)
 elif mode=='confirmation':
  winner=c.read(c.OUT/'development_decision.json')['winner'];st=repeats(rows,['O',winner]+(['S24'] if winner=='L24' else []),winner);result['stability']=st;tests={}
  for base in ['O','C']+(['S24'] if winner=='L24' else []):
   n=panels['natural'];q=panels['pressure'];tests[base]=dict(practical=g.practical(n['tables'][base],n['tables'][winner],n['paired'][winner+'__vs__'+base]),pressure=g.pressure_guard(q['tables'][base],q['tables'][winner]))
  test=tests['O'];status=g.confirmation_status(test['practical'],test['pressure'],st)
  decision=dict(winner=winner,status=status,tests=tests,stability_pass=not st['MCC_reversed'] if test['practical']['MCC_route_point'] else not st['risk_reversed'],
   mechanism_confirmed=winner=='L24' and g.confirmation_status(tests['S24']['practical'],tests['S24']['pressure'],st)=='确认通过',default_changed=False,
   interpretation='Useful simple baseline if S24 or EHR-all; L24 must also pass matched-length S24 before a whole-note mechanism claim')
 else:
  n=panels['natural'];q=panels['pressure'];comps={'P_vs_'+base:n['paired']['P__vs__'+base] for base in ['O','C','Q']}
  gates={base:old_gate(n['tables'],comps,base) for base in ['O','C','Q']};st=repeats(rows,['O','P','Q'],'P');result['stability']=st
  pressure=g.pressure_guard(q['tables']['O'],q['tables']['P']);stable=not any(st.get('original098_reversals',{}).values());ok=all(z['pass_all'] for z in gates.values()) and pressure['pass_all'] and stable
  point=all(z['checks']['MCC_effect'] and z['checks']['PA_floor'] and z['checks']['false_S_limit'] and z['checks']['minority_recall'] for z in gates.values())
  decision=dict(winner='P',status='确认通过' if ok else '点值改善但未确认' if point and pressure['pass_all'] else '失败停止',gates=gates,pressure=pressure,default_changed=False,stability_pass=stable)
 if mode!='development':c.put(c.OUT/'confirmation_decision.json',decision)
 result['decision']=decision;c.put(c.OUT/(mode+'_analysis.json'),result);c.putl(c.OUT/(mode+'_predictions.jsonl'),rows);c.putl(c.OUT/(mode+'_usage.jsonl'),usage);c.putl(c.OUT/(mode+'_attempt_ledger.jsonl'),ledger)
 with (c.OUT/(mode+'_main_table.csv')).open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['panel','configuration','N','MCC','PA','correct','false_S','non_S','NS_recall','NA_recall','Macro_F1'])
  for name,pp in panels.items():
   for arm,t in pp['tables'].items():w.writerow([name,arm,t['n'],t['mcc'],t['percent_agreement'],t['correct'],t['false_S'],t['true_non_S'],t['per_class']['Not Supported']['recall'],t['per_class']['Not Addressed']['recall'],t['Macro_F1']])
 c.put(c.OUT/(mode+'_cost_ledger.json'),dict(**rt.summary(),unknown_or_unverified_reservation_cny=sum(x['cost_or_reserved_cny'] for x in ledger if x['basis'].startswith('reserved')),retries=sum(x['attempt']>1 for x in ledger),logical_jobs=len(jobs),unique_successful_requests=len({j['request_id'] for j in jobs})))
 print(c.canonical(dict(phase=mode,decision=decision,cost=rt.summary())),flush=True)
if __name__=='__main__':main()
