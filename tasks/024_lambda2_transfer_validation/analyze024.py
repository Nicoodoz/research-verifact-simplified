"""Offline only. Requires every frozen request to have one valid terminal response."""
import argparse,json
from collections import Counter
from pathlib import Path
import common024 as c
ARMS=('B','V_raw','U0','U2','Always_S','O')
def run(out):
    c.require(not (c.OUT/'live.lock').exists(),'Live runner active')
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    c.require(len(terminal)==len(jobs)==3516,'Incomplete factorial; no available-case analysis')
    c.require(all(v['status']=='success' for v in terminal.values()),'Invalid terminal output')
    c.require(sum(a['charge_cny'] for a in attempts)<=c.CAP,'Budget exceeded')
    rows=c.csvread(c.OUT/'preparation_001/cohort.csv')
    logical={(j['proposition_id'],j['model_key'],j['arm']):terminal[j['request_id']] for j in jobs}
    historical={rep:c.csvread(c.ROOT/f'outputs/020_lambda2_patient_validation/analysis_001/predictions_r{rep}.csv') for rep in (0,1)}
    for rr in historical.values():c.require([r['proposition_id'] for r in rr]==[r['proposition_id'] for r in rows],'Historical ordered IDs changed')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    c.csvwrite(out/'attempt_costs.csv',attempts)
    c.put(out/'costs.json',dict(cap_cny=80,attempts=len(attempts),valid_terminal=len(terminal),usage_estimate_cny=sum(a['charge_cny'] for a in attempts if a['charge_basis']=='peak_no_cache_usage_estimate'),unknown_reservation_cny=sum(a['charge_cny'] for a in attempts if a['charge_basis']!='peak_no_cache_usage_estimate'),total_occupied_cny=sum(a['charge_cny'] for a in attempts),by_model={m:sum(a['charge_cny'] for a in attempts if a['model_key']==m) for m in c.MODELS},bill_reconciled=False))
    normalized=[dict(request_id=j['request_id'],proposition_id=j['proposition_id'],model_key=j['model_key'],arm=j['arm'],**terminal[j['request_id']]) for j in jobs]
    with (out/'normalized.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in normalized:f.write(c.canonical(r)+'\n')
    metrics={};paired={};patients=[];transitions=[];outcomes={};allpred={};historical_changes=[]
    for model in c.MODELS:
        bb=[logical[(r['proposition_id'],model,'B')] for r in rows]
        ss=[logical[(r['proposition_id'],model,'S')] for r in rows]
        preds={'B':[r['verdict'] for r in bb],'V_raw':[r['verdict'] for r in ss],'U0':[c.old.decision(r['scores'],0) for r in ss],'U2':[c.old.decision(r['scores'],2) for r in ss],'Always_S':['Supported']*len(rows),'O':[r['O'] for r in historical[0]]}
        allpred[model]=preds
        c.csvwrite(out/f'predictions_{model}.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],**{a:p[i] for a,p in preds.items()},**{'score_'+k:ss[i]['scores'][k] for k in c.LABELS}) for i,r in enumerate(rows)])
        for author in ('all','human','llm'):
            ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author];rr=[rows[i] for i in ix]
            for arm,pred in preds.items():
                pv=[pred[i] for i in ix];key=f'{model}/{author}/{arm}'
                m=c.old.evaluate(rr,c.old.prediction_rows(rr,pv));m['counts']=c.old.totals(rr,pv)
                non_s=len(rr)-m['counts']['support'].get('Supported',0)
                m['false_s_rate']=m['counts']['false_s']/non_s if non_s else None;m['false_s_denominator']=non_s
                metrics[key]=m
            for cand,base in [('U2','U0'),('U2','B'),('V_raw','B'),('U0','V_raw'),('U2','V_raw')]:
                paired[f'{model}/{author}/{cand}-minus-{base}']=c.old.paired_compare(rr,c.old.prediction_rows(rr,[preds[base][i] for i in ix]),c.old.prediction_rows(rr,[preds[cand][i] for i in ix]))
        for sid in sorted({r['subject_id'] for r in rows}):
            for author in ('all','human','llm'):
                ix=[i for i,r in enumerate(rows) if r['subject_id']==sid and (author=='all' or r['author_type']==author)]
                if not ix:continue
                rr=[rows[i] for i in ix]
                for arm in ARMS:
                    pp=[preds[arm][i] for i in ix];m=c.old.evaluate(rr,c.old.prediction_rows(rr,pp),profile='none');ct=c.old.totals(rr,pp)
                    patients.append(dict(model=model,subject_id=sid,author=author,arm=arm,n=len(ix),correct=ct['correct'],false_s=ct['false_s'],**{k:m[k] for k in ('percent_agreement','mcc','gwet_ac1')}))
        for i,r in enumerate(rows):
            g=r['human_gt'];u0=preds['U0'][i];u2=preds['U2'][i]
            rhw='R' if u0!='Supported' and u2=='Supported' and g=='Supported' else 'H' if u0==g!='Supported' and u2=='Supported' else 'W' if g!='Supported' and u0 not in (g,'Supported') and u2=='Supported' else ''
            transitions.append(dict(model=model,proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=g,B=preds['B'][i],V_raw=preds['V_raw'][i],U0=u0,U2=u2,RHW=rhw,raw_final_mismatch=preds['V_raw'][i]!=u2))
        results=[paired[f'{model}/all/U2-minus-{base}']['metrics'][metric] for base in ('U0','B') for metric in ('percent_agreement','mcc')]
        outcomes[model]=dict(direction_supported=all(v['delta']>0 for v in results),strong_transfer_evidence=all(v['ci95'][0]>0 for v in results))
        for rep,oldrows in historical.items():
            for arm in ('B','V_raw','U0','U2'):
                both=only_old=only_new=neither=flip=0
                for i,r in enumerate(rows):
                    a=oldrows[i][arm]==r['human_gt'];b=preds[arm][i]==r['human_gt']
                    both+=a and b;only_old+=a and not b;only_new+=b and not a;neither+=not a and not b;flip+=oldrows[i][arm]!=preds[arm][i]
                historical_changes.append(dict(new_model=model,historical_repeat=rep,arm=arm,both_correct=both,only_historical_correct=only_old,only_new_correct=only_new,both_wrong=neither,label_flips=flip,net_correct=only_new-only_old))
    for author in ('all','human','llm'):
        ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author];rr=[rows[i] for i in ix]
        for arm in ('B','V_raw','U0','U2'):
            paired[f'qwen-minus-deepseek/{author}/{arm}']=c.old.paired_compare(rr,c.old.prediction_rows(rr,[allpred['deepseek'][arm][i] for i in ix]),c.old.prediction_rows(rr,[allpred['qwen'][arm][i] for i in ix]))
    c.put(out/'metrics.json',metrics);c.put(out/'paired.json',paired);c.put(out/'decision.json',outcomes)
    c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'transitions.csv',transitions);c.csvwrite(out/'historical_comparison.csv',historical_changes)
    c.put(out/'response_metadata.json',dict(by_model={m:dict(returned_models=dict(Counter(r['model_returned'] for r in normalized if r['model_key']==m)),adherence_flags=dict(Counter(x for r in normalized if r['model_key']==m for x in r['adherence'])),input_tokens=sum(r['usage']['prompt_tokens'] for r in normalized if r['model_key']==m),output_tokens=sum(r['usage']['completion_tokens'] for r in normalized if r['model_key']==m)) for m in c.MODELS}))
    deps=list((c.OUT/'attempts').glob('*/*.json'))+[c.OUT/'preparation_001/manifest.json',Path(__file__),c.TASK/'common024.py',c.ROOT/'src/verifact_research/evaluation/core.py',c.ROOT/'src/verifact_research/evaluation/metrics.py']
    deps.extend(c.ROOT/f'outputs/020_lambda2_patient_validation/analysis_001/predictions_r{r}.csv' for r in (0,1))
    c.put(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in deps},outputs_sha256={p.name:c.file_hash(p) for p in out.iterdir() if p.is_file()}))
    print(c.canonical(outcomes))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay-dir');a=p.parse_args()
    target=c.OUT/'analysis_001'
    if a.replay_dir:
        target=Path(a.replay_dir).resolve();c.require(target.is_relative_to(c.ROOT/'outputs/replays'),'Replay must stay under outputs/replays')
    run(target)
