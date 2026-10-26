"""Evaluate only after all frozen calls finish; retain missing/invalid explicitly."""
import csv
import json
import statistics
import sys
from collections import Counter
from decimal import Decimal
import numpy as np
import common098 as c
import runtime098 as rt
from verifact_research.evaluation import evaluate, paired_compare
from sklearn.metrics import matthews_corrcoef, f1_score, confusion_matrix

ARMS = ['O','C','P','Q']
EPS = 1e-12  # Numerical tolerance only; preserve preregistered percentage boundaries.

def cohort(rows):
    return [dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows]

def predictions(rows, arm):
    return [dict(proposition_id=r['id'],verdict=r['predictions'][arm]) for r in rows]

def metric(rows, arm):
    result = evaluate(cohort(rows), predictions(rows,arm), profile='research_patient', iterations=1000)
    cm = np.array(result['confusion_matrix'])
    fs = int(cm[1:,0].sum()); non_s = int(cm[1:].sum()); pred_s = int(cm[:,0].sum())
    result.update(correct=int(np.trace(cm)),false_S=fs,true_non_S=non_s,false_S_rate=fs/non_s if non_s else None,
                  predicted_S=pred_s,false_discovery_S=fs/pred_s if pred_s else None,
                  Macro_F1=float(np.mean([result['per_class'][lab]['f1'] or 0 for lab in c.LABELS])))
    # Independent library cross-check; no alternative label mapping.
    y=[r['GT'] for r in rows]; z=[r['predictions'][arm] for r in rows]
    assert abs(matthews_corrcoef(y,z)-result['mcc'])<1e-10
    assert abs(f1_score(y,z,labels=list(c.LABELS),average='macro',zero_division=0)-result['Macro_F1'])<1e-10
    assert confusion_matrix(y,z,labels=list(c.LABELS)).tolist()==result['confusion_matrix']
    return result

def compare(rows, base, candidate):
    official=paired_compare(cohort(rows),predictions(rows,base),predictions(rows,candidate),iterations=1000)
    rescue=[r for r in rows if r['predictions'][base]!=r['GT'] and r['predictions'][candidate]==r['GT']]
    harm=[r for r in rows if r['predictions'][base]==r['GT'] and r['predictions'][candidate]!=r['GT']]
    non_s=sum(r['GT']!='Supported' for r in rows)
    added=sum(r['GT']!='Supported' and r['predictions'][base]!='Supported' and r['predictions'][candidate]=='Supported' for r in rows)
    prevented=sum(r['GT']!='Supported' and r['predictions'][base]=='Supported' and r['predictions'][candidate]!='Supported' for r in rows)
    patient={sid:sum(r in rescue for r in rows if r['sid']==sid)-sum(r in harm for r in rows if r['sid']==sid) for sid in sorted({r['sid'] for r in rows})}
    transitions=Counter((r['GT'],r['predictions'][base],r['predictions'][candidate]) for r in rows)
    # Supplemental false-S interval uses identical patient seed sequence.
    sids=sorted(patient); counts={sid:np.array([sum(r['GT']!='Supported' for r in rows if r['sid']==sid),
        sum(r['GT']!='Supported' and r['predictions'][base]=='Supported' for r in rows if r['sid']==sid),
        sum(r['GT']!='Supported' and r['predictions'][candidate]=='Supported' for r in rows if r['sid']==sid)]) for sid in sids}
    draws=[]
    for seed in range(1000):
        picked=np.random.RandomState(seed).choice(sids,len(sids),replace=True)
        n,b,p=sum((counts[s] for s in picked),start=np.zeros(3,dtype=int))
        if n:draws.append((p-b)/n)
    return dict(base=base,candidate=candidate,N=len(rows),patients=len(patient),paired=official,
                rescue=len(rescue),harm=len(harm),net=len(rescue)-len(harm),
                rescue_ids=[r['id'] for r in rescue],harm_ids=[r['id'] for r in harm],
                rescue_by_GT=dict(Counter(r['GT'] for r in rescue)),harm_by_GT=dict(Counter(r['GT'] for r in harm)),
                false_S_added=added,false_S_prevented=prevented,false_S_rate_delta=(added-prevented)/non_s if non_s else None,
                false_S_rate_delta_CI95=np.quantile(draws,[.025,.975]).tolist() if draws else None,
                patient_net=patient,patient_win_loss_tie=[sum(n>0 for n in patient.values()),sum(n<0 for n in patient.values()),sum(n==0 for n in patient.values())],
                class_transitions=[dict(GT=g,base=b,candidate=p,N=n) for (g,b,p),n in sorted(transitions.items())])

def gate(tables, comparisons, base):
    a,b=tables[base],tables['P']; cmp=comparisons['P_vs_'+base]
    dm=b['mcc']-a['mcc']; dp=b['percent_agreement']-a['percent_agreement']; df=b['false_S_rate']-a['false_S_rate']
    recall={lab:(b['per_class'][lab]['recall'] or 0)-(a['per_class'][lab]['recall'] or 0) for lab in ['Not Supported','Not Addressed']}
    ci=cmp['paired']['metrics']['mcc']['ci95']
    checks=dict(MCC_effect=dm>=.02-EPS,PA_floor=dp>=-.01-EPS,false_S_limit=df<=.02+EPS,minority_recall=all(v>=-.05-EPS for v in recall.values()),
                uncertainty_or_risk=(ci[0]>EPS or (df<=-.05+EPS and dp>=-EPS and dm>EPS)))
    return dict(pass_all=all(checks.values()),checks=checks,delta_MCC=dm,delta_PA=dp,delta_false_S_rate=df,delta_recall=recall)

def main():
    assert not (c.PRIVATE/'run.lock').exists(), 'Do not inspect target quality while calls active'
    frozen=c.read(c.OUT/'execution_freeze.json')
    for rel,checksum in frozen['files'].items():assert c.sha(c.ROOT/rel)==checksum,rel
    jobs=c.lines(c.PRIVATE/'jobs.jsonl'); done=rt.completed()
    assert all(j['request_id'] in done for j in jobs), 'Incomplete frozen panel: do not analyze partial results or select expansion'
    public={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')}
    records={pid:{**r,'predictions':dict(Original=r['Original']),'repeat_predictions':{},'arms':{},'repeat_arms':{}} for pid,r in public.items()}
    ledger=[]; usage=[]
    con=rt.db();attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
    total=Decimal(0)
    for rid,n,arm,charge,status,folder in attempts:
        folder=c.ROOT/folder; req=c.read(folder/'request.json');rp=folder/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None
        amount,basis=rt.accounting(req['job'],tr,req['reservation_cny'])
        assert abs(amount-charge)<1e-9
        total+=Decimal(str(amount))
        ledger.append(dict(request_id=rid,attempt=n,arm=arm,status=status,cost_or_reserved_cny=amount,basis=basis,
                           request_sha256=c.sha(folder/'request.json'),receipt_sha256=c.sha(rp) if rp.exists() else None,
                           folder=folder.relative_to(c.ROOT).as_posix(),started_utc=tr.get('started_utc') if tr else None,ended_utc=tr.get('ended_utc') if tr else None))
    attempt_costs={rid:sum(x['cost_or_reserved_cny'] for x in ledger if x['request_id']==rid) for rid in {x['request_id'] for x in ledger}}
    for j in jobs:
        folder=done[j['request_id']];req=c.read(folder/'request.json');tr=c.read(folder/'receipt.json')['transport']
        assert req['job']==j and req['endpoint']==c.ENDPOINT
        native=c.parse_native(tr)
        r=records[j['id']]; field='repeat_predictions' if j['repeat'] else 'predictions'; afield='repeat_arms' if j['repeat'] else 'arms'
        r[field][j['arm']]=native['verdict']
        response=json.loads(tr['body_text']);u=response['usage']
        r[afield][j['arm']]=dict(**native,request_id=j['request_id'],body_sha256=j['body_sha256'],receipt_sha256=c.sha(folder/'receipt.json'))
        usage.append(dict(id=j['id'],arm=j['arm'],panel=j['panel'],repeat=j['repeat'],request_id=j['request_id'],prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],cached_tokens=u.get('prompt_tokens_details',{}).get('cached_tokens',0),elapsed_seconds=tr['elapsed_seconds'],actual_or_reserved_cny=attempt_costs[j['request_id']],idle_no_cache_cny=(u['prompt_tokens']*1.5+u['completion_tokens']*4.5)/1e6))
    rows=list(records.values());panels={}
    for panel,arms in [('natural',ARMS),('pressure',['O','P'])]:
        allr=[r for r in rows if r['panel']==panel]
        common=[r for r in allr if all(r['predictions'].get(a) in c.LABELS for a in arms)]
        models=['Original']+arms
        tables={m:metric(common,m) for m in models}
        pairs={f'P_vs_{base}':compare(common,base,'P') for base in arms if base!='P'}
        if panel=='natural':pairs['C_vs_O']=compare(common,'O','C');pairs['Q_vs_O']=compare(common,'O','Q')
        coverage={m:dict(frozen_N=len(allr),valid=sum(r['predictions'].get(m) in c.LABELS for r in allr),invalid=sum(r['predictions'].get(m) not in c.LABELS for r in allr),correct_lower_bound=sum(r['predictions'].get(m)==r['GT'] for r in allr),
                         anomaly=sum(r['arms'].get(m,{}).get('format_anomaly',False) for r in allr)) for m in models}
        own={m:metric([r for r in allr if r['predictions'].get(m) in c.LABELS],m) for m in models}
        strata={author:{m:metric([r for r in common if r['author']==author],m) for m in models} for author in sorted({r['author'] for r in common})}
        panels[panel]=dict(frozen_N=len(allr),common_N=len(common),patients=len({r['sid'] for r in common}),GT=dict(Counter(r['GT'] for r in common)),tables=tables,paired=pairs,coverage=coverage,own_valid_metrics=own,by_author=strata)
    natural=panels['natural']
    frows=[r for r in rows if r['F_subset'] and all(r['predictions'].get(a) in c.LABELS for a in ['Original','O','C','P','Q','F'])]
    fdiag=dict(N=len(frows),tables={m:metric(frows,m) for m in ['Original','O','C','P','Q','F']},paired={f'{m}_vs_F':compare(frows,'F',m) for m in ['O','P','Q']})
    repeated=[r for r in rows if r['repeat_subset'] and all(r['repeat_predictions'].get(a) in c.LABELS and r['predictions'].get(a) in c.LABELS for a in ARMS)]
    second=[dict(r,predictions=dict(Original=r['Original'],**r['repeat_predictions'])) for r in repeated]
    stability=dict(frozen_N=sum(r['repeat_subset'] for r in rows),common_N=len(repeated),
         flips={a:sum(r['predictions'][a]!=r['repeat_predictions'][a] for r in repeated) for a in ARMS},
         first_tables={a:metric(repeated,a) for a in ['Original']+ARMS},second_tables={a:metric(second,a) for a in ['Original']+ARMS},
         first_pairs={f'P_vs_{a}':compare(repeated,a,'P') for a in ['O','C','Q']},second_pairs={f'P_vs_{a}':compare(second,a,'P') for a in ['O','C','Q']})
    gates={a:gate(natural['tables'],natural['paired'],a) for a in ['O','Q','C']}
    pressure=panels['pressure']['tables']
    pressure_checks=dict(minority_recall=all((pressure['P']['per_class'][lab]['recall'] or 0)-(pressure['O']['per_class'][lab]['recall'] or 0)>=-.1-EPS for lab in ['Not Supported','Not Addressed']),
                         false_S_limit=pressure['P']['false_S_rate']-pressure['O']['false_S_rate']<=.05+EPS)
    reversal={a:(stability['first_pairs']['P_vs_'+a]['paired']['metrics']['mcc']['delta']>0 and stability['first_pairs']['P_vs_'+a]['net']>0 and stability['second_pairs']['P_vs_'+a]['paired']['metrics']['mcc']['delta']<0 and stability['second_pairs']['P_vs_'+a]['net']<0) for a in ['O','Q']}
    decision=dict(gates=gates,pressure_checks=pressure_checks,repeat_direction_reversal=reversal,
       continue_candidate=all(gates[a]['pass_all'] for a in ['O','Q']) and all(pressure_checks.values()) and not any(reversal.values()),
       recommend_replace_C=all(gates[a]['pass_all'] for a in ['O','Q','C']) and all(pressure_checks.values()) and not any(reversal.values()),
       default_changed=False,independent_audit=False)
    c.putl(c.OUT/'predictions.jsonl',rows)
    c.putl(c.OUT/'attempt_ledger.jsonl',ledger)
    c.putl(c.OUT/'usage.jsonl',usage)
    c.put(c.OUT/'analysis.json',dict(panels=panels,F_diagnostic=fdiag,stability=stability,decision=decision,
         bootstrap_scope='Fixed predictions on historically exposed patients; no historical selection, retraining, service or external-hospital uncertainty.'))
    c.put(c.OUT/'decision.json',decision)
    cost=rt.summary();cost.update(total_decimal_cny=str(total),unknown_or_unverified_reservation_cny=sum(x['cost_or_reserved_cny'] for x in ledger if x['basis'].startswith('reserved')),
            retries=sum(r['attempt']>1 for r in ledger),target_requests=len(jobs),construction_requests=sum(r['arm']=='Q_construct' for r in ledger),
            independent_financial_bill=False,prices_verified='tasks/098_p90_native_confirmation/pricing_verification.md')
    c.put(c.OUT/'cost_ledger.json',cost)
    def cost_stats(us,arms):
        return {a:dict(N=len([u for u in us if u['arm']==a]),mean_input=statistics.mean(u['prompt_tokens'] for u in us if u['arm']==a),mean_output=statistics.mean(u['completion_tokens'] for u in us if u['arm']==a),mean_cached=statistics.mean(u['cached_tokens'] for u in us if u['arm']==a),mean_seconds=statistics.mean(u['elapsed_seconds'] for u in us if u['arm']==a),mean_actual_or_reserved_cny=statistics.mean(u['actual_or_reserved_cny'] for u in us if u['arm']==a),mean_idle_no_cache_cny=statistics.mean(u['idle_no_cache_cny'] for u in us if u['arm']==a)) for a in arms}
    fids={r['id'] for r in rows if r['F_subset']}
    primary=[u for u in usage if u['panel']=='natural' and not u['repeat']]
    stats=dict(natural_primary_same_ID=cost_stats(primary,ARMS),F_subset_same_ID=cost_stats([u for u in primary if u['id'] in fids],ARMS+['F']),
               all_calls_by_arm=cost_stats(usage,ARMS+['F']),
               note='Actual cache hits can depend on multi-arm/repeat execution. Matched single-arm comparisons also report idle no-cache cost from the same observed tokens; this is a normalized estimate, not an extra charge. Frozen P90 construction has historical cost outside this new-task ledger.')
    c.put(c.OUT/'usage_summary.json',stats)
    with (c.OUT/'main_table.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['panel','configuration','N','MCC','PA','correct','false_S','true_non_S','Macro_F1'])
        for panel,data in panels.items():
            for arm,t in data['tables'].items():w.writerow([panel,arm,t['n'],t['mcc'],t['percent_agreement'],t['correct'],t['false_S'],t['true_non_S'],t['Macro_F1']])
    print(c.canonical(dict(decision=decision,cost=cost,natural={a:dict(N=t['n'],correct=t['correct'],MCC=t['mcc'],false_S=t['false_S']) for a,t in natural['tables'].items()})))

if __name__=='__main__':main()
