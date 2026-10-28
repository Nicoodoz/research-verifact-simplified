"""Offline unified three-arm evaluation; never calls a model or changes a label."""
from pathlib import Path
from collections import Counter
import argparse
import sys
import numpy as np
import common105 as c
from parse105 import parse

sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare

def cohort(rows):return [dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows]
def preds(rows,key):return [dict(proposition_id=r['id'],verdict=r['pred'][key]) for r in rows]

def metric(rows,key,profile='research_patient'):
    result=evaluate(cohort(rows),preds(rows,key),profile=profile,iterations=1000)
    false=sum(r['GT']!='Supported' and r['pred'][key]=='Supported' for r in rows)
    nonS=sum(r['GT']!='Supported' for r in rows);predS=sum(r['pred'][key]=='Supported' for r in rows)
    result.update(correct=sum(r['GT']==r['pred'][key] for r in rows),false_S=false,non_S=nonS,
                  false_S_rate=false/nonS if nonS else None,predicted_S_FDR=false/predS if predS else None,
                  macro_F1=sum(result['per_class'][g]['f1'] or 0 for g in c.LABELS)/3)
    return result

def risk_deltas(rows,baseline,candidate):
    subjects=sorted({r['sid'] for r in rows});by={s:[r for r in rows if r['sid']==s] for s in subjects}
    def vector(part,key):
        denom=[sum(r['GT']!='Supported' for r in part),sum(r['GT']=='Not Supported' for r in part),sum(r['GT']=='Not Addressed' for r in part)]
        num=[sum(r['GT']!='Supported' and r['pred'][key]=='Supported' for r in part),sum(r['GT']==r['pred'][key]=='Not Supported' for r in part),sum(r['GT']==r['pred'][key]=='Not Addressed' for r in part)]
        return np.array([n/d if d else np.nan for n,d in zip(num,denom)])
    point=vector(rows,candidate)-vector(rows,baseline);draws=[]
    for seed in range(1000):
        picked=np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True)
        part=[r for i in picked for r in by[subjects[i]]];draws.append(vector(part,candidate)-vector(part,baseline))
    values=np.asarray(draws)
    return {name:dict(delta=float(point[i]),ci95=np.nanpercentile(values[:,i],[2.5,97.5]).tolist(),valid_draws=int(np.isfinite(values[:,i]).sum())) for i,name in enumerate(('false_S_rate','NS_recall','NA_recall'))}

def gate(natural,pressure):
    b=natural['label_only'];e=natural['evidence_brief'];base=natural['base_judge']
    required=[e['false_S_rate'],b['false_S_rate'],e['per_class']['Not Supported']['recall'],b['per_class']['Not Supported']['recall'],
              pressure['evidence_brief']['false_S_rate'],pressure['label_only']['false_S_rate'],
              pressure['evidence_brief']['per_class']['Not Supported']['recall'],pressure['label_only']['per_class']['Not Supported']['recall']]
    if any(value is None for value in required):return dict(conditions={},point_development_gate_pass=False,undefined_denominator=True,not_paper_confirmation=True)
    delta=dict(MCC=e['mcc']-b['mcc'],PA=e['percent_agreement']-b['percent_agreement'],false_S=e['false_S_rate']-b['false_S_rate'],NS=e['per_class']['Not Supported']['recall']-b['per_class']['Not Supported']['recall'])
    p=pressure['evidence_brief'];q=pressure['label_only']
    conditions=dict(improvement=delta['MCC']>=.02-1e-12 or delta['false_S']<=-.05+1e-12,
        PA=delta['PA']>=-.02-1e-12,false_S=delta['false_S']<=.02+1e-12,NS=delta['NS']>=-.05-1e-12,
        pressure_false_S=p['false_S_rate']<=q['false_S_rate']+1e-12,
        pressure_NS=p['per_class']['Not Supported']['recall']>=q['per_class']['Not Supported']['recall']-.05-1e-12,
        base_guard=not (e['mcc']<base['mcc'] and e['false_S_rate']>base['false_S_rate']))
    return dict(delta=delta,conditions=conditions,point_development_gate_pass=all(conditions.values()),not_paper_confirmation=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,required=True);p.add_argument('--keys',type=Path,default=c.OUT/'eval_keys.jsonl')
    p.add_argument('--output',type=Path,default=c.OUT/'evaluation.json');a=p.parse_args()
    keys=c.rows(a.keys);expected={r['id'] for r in keys};data={};coverage={}
    for arm in c.ARMS:
        records=[]
        for path in sorted((a.results/'eval'/arm).glob('batch-*.json')):
            if '.inflight.' in path.name:continue
            records+=c.read(path)['records']
        assert len({r['id'] for r in records})==len(records)
        assert {r['id'] for r in records}<=expected
        data[arm]={r['id']:dict(r,parsed=parse(r['content'],r['finish_reason'])) for r in records}
        coverage[arm]=dict(frozen_N=len(keys),received=len(records),valid=sum(r['parsed']['valid'] for r in data[arm].values()),
                           invalid=sum(not r['parsed']['valid'] for r in data[arm].values()),missing=len(expected-set(data[arm])))
    paired=[]
    for key in keys:
        if all(key['id'] in data[arm] and data[arm][key['id']]['parsed']['valid'] for arm in c.ARMS):
            paired.append(dict(key,pred={**{arm:data[arm][key['id']]['parsed']['verdict'] for arm in c.ARMS},'paper_r1':key['paper_r1']}))
    results={};metrics={}
    for panel in ('natural','pressure'):
        rows=[r for r in paired if r['panel']==panel]
        if len({r['sid'] for r in rows})<2:raise ValueError('Not enough complete paired patients; report execution incomplete')
        metrics[panel]={arm:metric(rows,arm) for arm in (*c.ARMS,'paper_r1')}
        comparisons={}
        for baseline,candidate in [('label_only','evidence_brief'),('base_judge','evidence_brief'),('base_judge','label_only')]:
            comparisons[candidate+'__vs__'+baseline]=dict(primary=paired_compare(cohort(rows),preds(rows,baseline),preds(rows,candidate)),
                risk=risk_deltas(rows,baseline,candidate),rescued=sum(r['pred'][baseline]!=r['GT']==r['pred'][candidate] for r in rows),
                harmed=sum(r['pred'][baseline]==r['GT']!=r['pred'][candidate] for r in rows))
        full=[r for r in keys if r['panel']==panel]
        per_arm_full={}
        for arm in c.ARMS:
            good=[r for r in full if r['id'] in data[arm] and data[arm][r['id']]['parsed']['valid']]
            correct=sum(data[arm][r['id']]['parsed']['verdict']==r['GT'] for r in good)
            false=sum(r['GT']!='Supported' and data[arm][r['id']]['parsed']['verdict']=='Supported' for r in good)
            nonS=sum(r['GT']!='Supported' for r in full);invalid_nonS=sum(r['GT']!='Supported' and r not in good for r in full)
            per_arm_full[arm]=dict(N=len(full),valid=len(good),missing_or_invalid=len(full)-len(good),
                PA_full_bounds=[correct/len(full),(correct+len(full)-len(good))/len(full)],
                false_S_full_bounds=[false/nonS,(false+invalid_nonS)/nonS])
        results[panel]=dict(frozen_N=len(full),common_valid_N=len(rows),metrics=metrics[panel],paired=comparisons,full_N_coverage=per_arm_full,
            author={author:{arm:metric([r for r in rows if r['author']==author],arm,profile='none') for arm in (*c.ARMS,'paper_r1')} for author in ('human','llm') if any(r['author']==author for r in rows)})
    decision=gate(metrics['natural'],metrics['pressure'])
    complete=all(r['missing']==0 for r in coverage.values())
    enough=all(results[p]['common_valid_N']/results[p]['frozen_N']>=.95 for p in results)
    decision.update(all_frozen_requests_complete=complete,common_coverage_at_least_95pct=enough,
                    continue_to_larger_training=complete and enough and decision['point_development_gate_pass'])
    c.put(a.output,dict(panels=results,coverage=coverage,decision=decision,natural_and_pressure_never_pooled=True,
                        missing_invalid_no_fallback=True,bootstrap='1000 paired patient clusters',current_same_Judge_verifact_ref_not_run=True,
                        paper_r1_historical_only=True))
    print(c.canonical(decision))

if __name__=='__main__':main()
