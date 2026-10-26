"""No interim quality analysis; same-ID direct verdict metrics and frozen selection."""
from collections import Counter
from decimal import Decimal
import csv
import itertools
import json
import statistics
import numpy as np
from sklearn.metrics import matthews_corrcoef,f1_score
import common099 as c
import runtime099 as rt
from parse099 import parse as parse_normalized
from verifact_research.evaluation import evaluate,paired_compare

def cohort(rows):return [dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows]
def preds(rows,m):return [dict(proposition_id=r['id'],verdict=r['predictions'][m]) for r in rows]

def metric(rows,m):
    profile='research_patient' if len({r['sid'] for r in rows})>=2 else 'none'
    t=evaluate(cohort(rows),preds(rows,m),profile=profile,iterations=1000)
    cm=np.array(t['confusion_matrix']);fs=int(cm[1:,0].sum());nonS=int(cm[1:].sum());predS=int(cm[:,0].sum())
    y=[r['GT'] for r in rows];p=[r['predictions'][m] for r in rows]
    macro=f1_score(y,p,labels=list(c.LABELS),average='macro',zero_division=0)
    assert abs(matthews_corrcoef(y,p)-t['mcc'])<1e-10
    t.update(correct=int(np.trace(cm)),false_S=fs,true_non_S=nonS,false_S_rate=fs/nonS if nonS else None,
             predicted_S=predS,false_discovery_S=fs/predS if predS else None,Macro_F1=float(macro))
    return t

def pair(rows,base,new):
    out=paired_compare(cohort(rows),preds(rows,base),preds(rows,new),iterations=1000)
    rescue=[r for r in rows if r['predictions'][base]!=r['GT'] and r['predictions'][new]==r['GT']]
    harm=[r for r in rows if r['predictions'][base]==r['GT'] and r['predictions'][new]!=r['GT']]
    added=sum(r['GT']!='Supported' and r['predictions'][base]!='Supported' and r['predictions'][new]=='Supported' for r in rows)
    prevented=sum(r['GT']!='Supported' and r['predictions'][base]=='Supported' and r['predictions'][new]!='Supported' for r in rows)
    patients={s:sum(r['sid']==s for r in rescue)-sum(r['sid']==s for r in harm) for s in sorted({r['sid'] for r in rows})}
    return dict(base=base,candidate=new,N=len(rows),rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),
                rescue_ids=[r['id'] for r in rescue],harm_ids=[r['id'] for r in harm],false_S_added=added,false_S_prevented=prevented,
                patient_net=patients,patient_win_loss_tie=[sum(v>0 for v in patients.values()),sum(v<0 for v in patients.values()),sum(v==0 for v in patients.values())],paired=out,
                transitions=[dict(GT=g,base=b,candidate=p,N=n) for (g,b,p),n in sorted(Counter((r['GT'],r['predictions'][base],r['predictions'][new]) for r in rows).items())])

def panel(rows,models,reference_models=(),common_ids=None):
    common=[r for r in rows if all(r['predictions'].get(m) in c.LABELS for m in models) and (common_ids is None or r['id'] in common_ids)]
    coverage={m:dict(frozen_N=len(rows),valid=sum(r['predictions'].get(m) in c.LABELS for r in rows),invalid=sum(r['predictions'].get(m) not in c.LABELS for r in rows),known_correct=sum(r['predictions'].get(m)==r['GT'] for r in rows),
                    anomaly=sum(r.get('arms',{}).get(m,{}).get('format_anomaly',False) for r in rows)) for m in models}
    tables={m:metric(common,m) for m in ['Original']+list(models)} if common else {}
    # A separately labelled historical reference may lack a value; never silently impute.
    historical={}
    for m in reference_models:
        rr=[r for r in common if r['predictions'].get(m) in c.LABELS]
        if rr:historical[m]=dict(N=len(rr),metrics=metric(rr,m))
    comparisons={f'{new}__vs__{base}':pair(common,base,new) for base,new in itertools.combinations(models,2)} if len({r['sid'] for r in common})>=2 else {}
    return dict(frozen_N=len(rows),common_N=len(common),patients=len({r['sid'] for r in common}),GT=dict(Counter(r['GT'] for r in common)),
                coverage=coverage,tables=tables,paired=comparisons,historical=historical,
                own_valid_metrics={m:metric([r for r in rows if r['predictions'].get(m) in c.LABELS],m) if any(r['predictions'].get(m) in c.LABELS for r in rows) else None for m in models},
                by_author={author:{m:metric([r for r in common if r['author']==author],m) for m in ['Original']+list(models)} for author in sorted({r['author'] for r in common})})

def select(main,diagnostic,costs):
    eligible=[];floors={};eps=1e-12
    for m in c.MODELS:
        t=main['tables'][m];d=diagnostic['tables'][m];cov=main['coverage'][m]
        checks=dict(coverage=cov['valid']/cov['frozen_N']>=.95-eps,
                    PA_floor=t['percent_agreement']>=main['tables']['Original']['percent_agreement']-.05-eps,
                    NS_diagnostic=(d['per_class']['Not Supported']['recall'] or 0)>=.2-eps,
                    NA_diagnostic=(d['per_class']['Not Addressed']['recall'] or 0)>=.2-eps)
        floors[m]=dict(checks=checks,pass_all=all(checks.values()),single_A800_high_fidelity=m!='qwen3.8-flash')
        if all(checks.values()) and m!='qwen3.8-flash':eligible.append(m)
    deployable=[m for m in c.MODELS if m!='qwen3.8-flash']
    leader=max(eligible or deployable,key=lambda m:(main['tables'][m]['mcc'],-main['tables'][m]['false_S'],main['tables'][m]['percent_agreement']))
    if eligible:
        near=[m for m in eligible if main['tables'][m]['mcc']>=main['tables'][leader]['mcc']-.02-eps and main['tables'][m]['percent_agreement']>=main['tables'][leader]['percent_agreement']-.02-eps]
        minFS=min(main['tables'][m]['false_S'] for m in near);maxPA=max(main['tables'][m]['percent_agreement'] for m in near)
        risknear=[m for m in near if main['tables'][m]['false_S']<=minFS+1 and main['tables'][m]['percent_agreement']>=maxPA-.01-eps]
        primary=min(risknear,key=lambda m:(costs[m]['mean_no_cache_cny'],m=='qwen3.5-35b-a3b'))
    else:near=[];risknear=[];primary=leader
    alternatives=sorted([m for m in deployable if m!=primary],key=lambda m:(not floors[m]['pass_all'],-main['tables'][m]['mcc'],main['tables'][m]['false_S'],costs[m]['mean_no_cache_cny']))
    overall=max(c.MODELS,key=lambda m:(main['tables'][m]['mcc'],-main['tables'][m]['false_S'],main['tables'][m]['percent_agreement']))
    return dict(primary=primary,backup=alternatives[0],API_point_leader=overall,floors=floors,MCC_leader_deployable=leader,eligible=eligible,practical_nearby=near,risk_cost_nearby=risknear,
                primary_is_conditional=not bool(eligible),default_changed=False,
                decision_basis='O natural direct verdict first; predefined deployment and cost tie-breaks; never C-O improvement or PriorG',
                warning='Small exposed selection panel: recommendation is provisional, not demonstrated population-wide model superiority or API/local equivalence.')

def main():
    assert not (c.PRIVATE/'run.lock').exists()
    freeze=c.read(c.OUT/'execution_freeze.json')
    for rel,d in freeze['files'].items():assert c.sha(c.ROOT/rel)==d,rel
    jobs=c.lines(c.PRIVATE/'jobs.jsonl');done=rt.completed()
    assert all(j['request_id'] in done for j in jobs),'Incomplete frozen calls: no partial-quality selection'
    amendment=c.read(c.OUT/'format_amendment_freeze.json')
    for rel,d in amendment['files'].items():assert c.sha(c.ROOT/rel)==d,rel
    public=c.lines(c.OUT/'cohort.jsonl');records={r['id']:{**r,'O_predictions':dict(Original=r['Original'],V4_097=r['V4_097_O']),'C_predictions':dict(Original=r['Original'],V4_097=r['V4_097_C']),
                'repeat_predictions':dict(Original=r['Original']),'O_strict':dict(Original=r['Original']),'C_strict':dict(Original=r['Original']),'repeat_strict':dict(Original=r['Original']),
                'O_arms':{},'C_arms':{},'repeat_arms':{}} for r in public}
    usage=[];ledger=[]
    con=rt.db();attempts=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
    for rid,n,model,amount,status,folder in attempts:
        p=c.ROOT/folder;req=c.read(p/'request.json');receipt=c.read(p/'receipt.json');account=c.read(p/'accounting.json');tr=receipt['transport']
        recalculated,basis=rt.charge(req['job'],tr,req['reservation_cny']);assert abs(recalculated-amount)<1e-10
        ledger.append(dict(request_id=rid,attempt=n,model=model,status=status,cost_or_reserved_cny=amount,basis=basis,folder=folder,request_sha256=c.sha(p/'request.json'),receipt_sha256=c.sha(p/'receipt.json'),started_utc=tr['started_utc'],ended_utc=tr['ended_utc']))
    cost_by_id={rid:sum(x['cost_or_reserved_cny'] for x in ledger if x['request_id']==rid) for rid in {x['request_id'] for x in ledger}}
    for j in jobs:
        folder=done[j['request_id']];req=c.read(folder/'request.json');tr=c.read(folder/'receipt.json')['transport'];assert req['job']==j
        parsed=parse_normalized(tr);strict=c.parse(tr);r=records[j['id']];prefix='repeat' if j['repeat'] else j['context'];r[prefix+'_predictions'][j['model']]=parsed['verdict'];r[prefix+'_strict'][j['model']]=strict['verdict']
        r[prefix+'_arms'][j['model']]=dict(**parsed,request_id=j['request_id'],body_sha256=j['body_sha256'],receipt_sha256=c.sha(folder/'receipt.json'))
        response=json.loads(tr['body_text']);u=response['usage'];ip,op,_=rt.price(j['model'],u['prompt_tokens']);detail=u.get('completion_tokens_details') or {}
        usage.append(dict(id=j['id'],model=j['model'],context=j['context'],panel=j['panel'],repeat=j['repeat'],prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],reasoning_tokens=detail.get('reasoning_tokens'),
                          cached_tokens=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0),elapsed_seconds=tr['elapsed_seconds'],actual_cny=cost_by_id[j['request_id']],no_cache_cny=(u['prompt_tokens']*ip+u['completion_tokens']*op)/1e6,
                          output_over_requested_envelope=u['completion_tokens']>c.THINKING+c.ANSWER+32,finish_reason=response['choices'][0].get('finish_reason')))
    rows=list(records.values())
    rr=lambda panel_name,context,subset=False:[dict(r,predictions=r[context+'_predictions'],arms=r[context+'_arms']) for r in rows if r['panel']==panel_name and (not subset or r['C_subset'])]
    main_O=panel(rr('natural','O'),list(c.MODELS),['V4_097'])
    strict_O=panel([dict(r,predictions=r['O_strict'],arms={m:dict(format_anomaly=not r['O_arms'].get(m,{}).get('strict_valid',False)) for m in c.MODELS}) for r in rows if r['panel']=='natural'],list(c.MODELS))
    Cjoint={r['id'] for r in rows if r['C_subset'] and all(r['O_predictions'].get(m) in c.LABELS and r['C_predictions'].get(m) in c.LABELS for m in c.MODELS)}
    Csubset=panel(rr('natural','C',True),list(c.MODELS),['V4_097'],common_ids=Cjoint)
    Omatched=panel(rr('natural','O',True),list(c.MODELS),['V4_097'],common_ids=Cjoint)
    diag=panel(rr('diagnostic','O'),list(c.MODELS))
    rep0=[dict(r,predictions=r['O_predictions']) for r in rows if r['repeat_subset'] and all(r['O_predictions'].get(m) in c.LABELS and r['repeat_predictions'].get(m) in c.LABELS for m in c.MODELS)]
    rep1=[dict(r,predictions=r['repeat_predictions']) for r in rows if r['repeat_subset'] and all(r['O_predictions'].get(m) in c.LABELS and r['repeat_predictions'].get(m) in c.LABELS for m in c.MODELS)]
    stability=dict(frozen_N=8,common_N=len(rep0),flips={m:sum(r['O_predictions'][m]!=r['repeat_predictions'][m] for r in rep0) for m in c.MODELS},
                   first={m:metric(rep0,m) for m in c.MODELS} if rep0 else {},second={m:metric(rep1,m) for m in c.MODELS} if rep1 else {})
    coststats={m:dict(N=len([u for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat']]),
         mean_no_cache_cny=statistics.mean(u['no_cache_cny'] for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat']),
         mean_actual_cny=statistics.mean(u['actual_cny'] for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat']),
         mean_input=statistics.mean(u['prompt_tokens'] for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat']),
         mean_output=statistics.mean(u['completion_tokens'] for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat']),
         mean_seconds=statistics.mean(u['elapsed_seconds'] for u in usage if u['model']==m and u['context']=='O' and u['panel']=='natural' and not u['repeat'])) for m in c.MODELS}
    selection=select(main_O,diag,coststats)
    strict_diag=panel([dict(r,predictions=r['O_strict']) for r in rows if r['panel']=='diagnostic'],list(c.MODELS))
    strict_selection=select(strict_O,strict_diag,coststats) if strict_O['common_N'] and strict_diag['common_N'] else dict(primary=None,reason='No common valid cohort under strict raw JSON format')
    transfers={}
    for m in c.MODELS:
        matched=[dict(r,predictions=dict(O=r['O_predictions'].get(m),C=r['C_predictions'].get(m))) for r in rows if r['id'] in Cjoint]
        transfers[m]=pair(matched,'O','C')
    c.putl(c.OUT/'predictions.jsonl',rows);c.putl(c.OUT/'usage.jsonl',usage);c.putl(c.OUT/'attempt_ledger.jsonl',ledger)
    c.put(c.OUT/'analysis.json',dict(O_natural=main_O,C_subset=Csubset,O_matched_C_subset=Omatched,diagnostic=diag,stability=stability,O_to_C=transfers,cost_natural_O=coststats,selection=selection,
         strict_format_sensitivity=dict(O_natural=strict_O,diagnostic=strict_diag,selection=strict_selection,primary_same=strict_selection['primary']==selection['primary']),
         bootstrap_scope='Fixed predictions on historically exposed selection patients; excludes historical selection, stochastic API calls, retraining and new-hospital generalization.'))
    c.put(c.OUT/'selection.json',selection)
    cost=rt.summary();cost.update(retries=sum(x['attempt']>1 for x in ledger),unknown_reservation_cny=sum(x['cost_or_reserved_cny'] for x in ledger if x['basis']!='verified_usage'),
        total_decimal_cny=str(sum((Decimal(str(x['cost_or_reserved_cny'])) for x in ledger),start=Decimal(0))),independent_financial_bill=False,
        output_envelope_violations=sum(u['output_over_requested_envelope'] for u in usage),prior099_cost_cny=0)
    c.put(c.OUT/'cost_ledger.json',cost)
    with (c.OUT/'main_table.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['panel','model','N','MCC','PA','correct','false_S','true_non_S','Macro_F1'])
        for name,pp in [('O_natural',main_O),('C_subset',Csubset),('O_matched_C_subset',Omatched),('diagnostic_O',diag)]:
            for m,t in pp['tables'].items():w.writerow([name,m,t['n'],t['mcc'],t['percent_agreement'],t['correct'],t['false_S'],t['true_non_S'],t['Macro_F1']])
    print(c.canonical(dict(selection=selection,cost=cost,main={m:dict(correct=t['correct'],MCC=t['mcc'],PA=t['percent_agreement'],false_S=t['false_S']) for m,t in main_O['tables'].items()})))

if __name__=='__main__':main()
