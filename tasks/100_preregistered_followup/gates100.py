"""Pure preregistered decisions; no raw data, labels, files or network."""
EPS=1e-12
ORDER=['S24','L24','EHR-all']
def delta(base,new):
 return dict(MCC=new['mcc']-base['mcc'],PA=new['percent_agreement']-base['percent_agreement'],false_S_rate=new['false_S_rate']-base['false_S_rate'],
  NS_recall=(new['per_class']['Not Supported']['recall'] or 0)-(base['per_class']['Not Supported']['recall'] or 0),NA_recall=(new['per_class']['Not Addressed']['recall'] or 0)-(base['per_class']['Not Addressed']['recall'] or 0))
def development_select(natural,pressure,coverage,costs):
 checks={};eligible=[]
 for arm in ORDER:
  if coverage[arm]<.95-EPS or arm not in natural:
   checks[arm]=dict(eligible=False,veto=['valid_coverage_below95'],coverage=coverage[arm]);continue
  d=delta(natural['O'],natural[arm]);p=delta(pressure['O'],pressure[arm]);veto=[]
  if d['PA']<-.05-EPS:veto.append('natural_PA_drop_over5pp')
  if p['false_S_rate']>.0625+EPS:veto.append('pressure_falseS_increase_over6.25pp')
  if min(p['NS_recall'],p['NA_recall'])<-.2-EPS:veto.append('pressure_class_recall_drop_over20pp')
  A=d['MCC']>=-.02-EPS and d['PA']>=-.02-EPS
  B=p['false_S_rate']<=-.0625+EPS and d['MCC']>=-.05-EPS and d['PA']>=-.035-EPS
  ok=not veto and (A or B);checks[arm]=dict(eligible=ok,veto=veto,path_A=A,path_B=B,natural_delta=d,pressure_delta=p,coverage=coverage[arm])
  if ok:eligible.append(arm)
 if not eligible:return dict(winner=None,checks=checks,eligible=[],nearby=[],status='失败停止',reason='All three fixed candidates rejected; no confirmation API or new candidate')
 leader=max(eligible,key=lambda a:natural[a]['mcc']);near=[a for a in eligible if natural[a]['mcc']>=natural[leader]['mcc']-.03-EPS]
 winner=min(near,key=lambda a:(pressure[a]['false_S'],-natural[a]['percent_agreement'],costs[a],ORDER.index(a)))
 return dict(winner=winner,checks=checks,eligible=eligible,MCC_leader=leader,nearby=near,status='development_complete_confirm_one',rule='MCC nearby0.03 -> pressure falseS -> natural PA -> matched no-cache actual token cost -> S/L/E identical tie')
def practical(base,new,comparison):
 d=delta(base,new);mcc=d['MCC']>=.03-EPS and d['PA']>=-.02-EPS and d['false_S_rate']<=.02+EPS
 risk=d['false_S_rate']<=-.05+EPS and d['MCC']>=-.01-EPS and d['PA']>=-.02-EPS
 ci=comparison['paired']['metrics']['mcc']['ci95'];fci=comparison['false_S_rate_delta_CI95']
 return dict(delta=d,MCC_route_point=mcc,risk_route_point=risk,point_pass=mcc or risk,MCC_CI_support=ci[0]>EPS,risk_CI_support=fci is not None and fci[1]<-EPS,
  uncertainty_pass=(mcc and ci[0]>EPS) or (risk and fci is not None and fci[1]<-EPS))
def pressure_guard(base,new):
 d=delta(base,new);return dict(delta=d,false_S_limit=d['false_S_rate']<=.05+EPS,NS_recall_limit=d['NS_recall']>=-.1-EPS,NA_recall_limit=d['NA_recall']>=-.1-EPS,pass_all=d['false_S_rate']<=.05+EPS and min(d['NS_recall'],d['NA_recall'])>=-.1-EPS)
def confirmation_status(test,pressure,repeat):
 stable_mcc=not repeat.get('MCC_reversed',False);stable_risk=not repeat.get('risk_reversed',False)
 stable_route=(test['MCC_route_point'] and test['MCC_CI_support'] and stable_mcc) or (test['risk_route_point'] and test['risk_CI_support'] and stable_risk)
 if test['point_pass'] and pressure['pass_all'] and stable_route:return '确认通过'
 if test['point_pass'] and pressure['pass_all']:return '点值改善但未确认'
 return '失败停止'
