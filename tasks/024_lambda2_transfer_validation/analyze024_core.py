"""002 paired complete-case analysis with explicit per-comparison cohort identities."""
import argparse
from collections import Counter
from pathlib import Path
import core024 as c

def metrics(rows,pp,profile='research_patient'):
    m=c.old.evaluate(rows,c.old.prediction_rows(rows,pp),profile=profile)
    m['counts']=c.old.totals(rows,pp);non_s=sum(r['human_gt']!='Supported' for r in rows)
    m.update(false_s_denominator=non_s,false_s_rate=m['counts']['false_s']/non_s if non_s else None)
    return m
def select(rows,arms):
    ids={r['proposition_id'] for r in rows}
    for a in arms:ids&={k for k,v in a.items() if v is not None}
    return [r for r in rows if r['proposition_id'] in ids]
def cohort_record(full,selected):
    ids=[r['proposition_id'] for r in selected];ids_set=set(ids)
    return dict(expected_n=len(full),valid_n=len(ids),missing_n=len(full)-len(ids),included_ids=ids,excluded_ids=[r['proposition_id'] for r in full if r['proposition_id'] not in ids_set],ordered_cohort_sha256=c.fingerprint([[r['proposition_id'],r['subject_id'],r['human_gt']] for r in selected]))
def run(out):
    c.require(not (c.OUT/'live.lock').exists(),'Runner active')
    jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);cnt=Counter(a['request_id'] for a in attempts)
    c.require(all(j['request_id'] in term or cnt[j['request_id']]>=3 for j in jobs),'Unexecuted/eligible requests remain')
    c.require(sum(a['charge_cny'] for a in attempts)<=80,'Budget exceeded')
    rows=c.csvread(c.OUT/'preparation_001/cohort.csv');ids=[r['proposition_id'] for r in rows]
    c.require(len(rows)==879 and len(set(ids))==879,'Frozen denominator changed')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    hist={rep:c.csvread(c.ROOT/f'outputs/020_lambda2_patient_validation/analysis_001/predictions_r{rep}.csv') for rep in (0,1)}
    for rr in hist.values():c.require([r['proposition_id'] for r in rr]==ids,'Historical identity mismatch')
    logical={(j['proposition_id'],j['model_key'],j['arm']):term.get(j['request_id']) for j in jobs}
    preds={};norm=[];missing=[]
    for j in jobs:
        v=term.get(j['request_id'],dict(status='invalid_core_fields',errors=['no_http200_after_three_attempts'],adherence=[]))
        norm.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],model_key=j['model_key'],arm=j['arm'],**v))
        if v['status'] not in c.VALID:missing.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],model_key=j['model_key'],arm=j['arm'],status=v['status'],errors=';'.join(v['errors'])))
    with (out/'normalized.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in norm:f.write(c.canonical(r)+'\n')
    c.put(out/'invalid_missing.json',missing)
    for model in c.MODELS:
        ps={a:{} for a in ('B','V_raw','U0','U2','Always_S','O')};export=[]
        for i,r in enumerate(rows):
            pid=r['proposition_id'];b=logical[(pid,model,'B')];s=logical[(pid,model,'S')]
            bv=b and b['status'] in c.VALID;sv=s and s['status'] in c.VALID
            pp=dict(B=b['verdict'] if bv else None,V_raw=s['verdict'] if sv else None,U0=c.old.decision(s['scores'],0) if sv else None,U2=c.old.decision(s['scores'],2) if sv else None,Always_S='Supported',O=hist[0][i]['O'])
            for a,v in pp.items():ps[a][pid]=v
            export.append(dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],B_status=b['status'] if b else 'missing',S_status=s['status'] if s else 'missing',**pp,**{'score_'+label:s['scores'][label] if sv else None for label in c.LABELS}))
        preds[model]=ps;c.csvwrite(out/f'predictions_{model}.csv',export)
    allmetrics={};paired={};cohorts={};patients=[];transitions=[];sensitivity=[];historical=[]
    def compare(key,full,bp,cp):
        rr=select(full,[bp,cp]);require_n=len(rr)
        c.require(require_n>0,'Empty comparison: '+key)
        b=[bp[r['proposition_id']] for r in rr];s=[cp[r['proposition_id']] for r in rr]
        q=c.old.paired_compare(rr,c.old.prediction_rows(rr,b),c.old.prediction_rows(rr,s))
        q.update(baseline=metrics(rr,b,'none'),candidate=metrics(rr,s,'none'),net_correct=sum(x==r['human_gt'] for x,r in zip(s,rr))-sum(x==r['human_gt'] for x,r in zip(b,rr)))
        paired[key]=q;cohorts[key]=cohort_record(full,rr)
    for model,ps in preds.items():
        for author in ('all','human','llm'):
            full=[r for r in rows if author=='all' or r['author_type']==author]
            main=select(full,[ps['B'],ps['U2']]);cohorts[f'{model}/{author}/main_B_S']=cohort_record(full,main)
            for a in ps:
                allmetrics[f'{model}/{author}/{a}']=metrics(main,[ps[a][r['proposition_id']] for r in main])
                valid=select(full,[ps[a]]);correct=sum(ps[a][r['proposition_id']]==r['human_gt'] for r in valid)
                sensitivity.append(dict(model=model,author=author,arm=a,frozen_n=len(full),valid_n=len(valid),missing_n=len(full)-len(valid),correct=correct,missing_as_error_pa=correct/len(full),optimistic_pa_bound=(correct+len(full)-len(valid))/len(full)))
            for cand,base in [('U2','U0'),('U2','B'),('V_raw','B'),('U0','V_raw'),('U2','V_raw')]:compare(f'{model}/{author}/{cand}-minus-{base}',full,ps[base],ps[cand])
        main=select(rows,[ps['B'],ps['U2']])
        for sid in sorted({r['subject_id'] for r in rows}):
            for author in ('all','human','llm'):
                rr=[r for r in main if r['subject_id']==sid and (author=='all' or r['author_type']==author)]
                if not rr:continue
                for a in ps:
                    m=metrics(rr,[ps[a][r['proposition_id']] for r in rr],'none')
                    patients.append(dict(model=model,subject_id=sid,author=author,arm=a,n=len(rr),correct=m['counts']['correct'],false_s=m['counts']['false_s'],**{k:m[k] for k in ('percent_agreement','mcc','gwet_ac1')}))
        for r in select(rows,[ps['U0'],ps['U2']]):
            pid=r['proposition_id'];g=r['human_gt'];u0=ps['U0'][pid];u2=ps['U2'][pid]
            rhw='R' if u0!='Supported' and u2=='Supported' and g=='Supported' else 'H' if u0==g!='Supported' and u2=='Supported' else 'W' if g!='Supported' and u0 not in (g,'Supported') and u2=='Supported' else ''
            transitions.append(dict(model=model,proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],GT=g,B=ps['B'][pid],V_raw=ps['V_raw'][pid],U0=u0,U2=u2,RHW=rhw,raw_final_mismatch=ps['V_raw'][pid]!=u2))
        for rep,rr in hist.items():
            hm={r['proposition_id']:r for r in rr}
            for arm in ('B','V_raw','U0','U2'):
                cohort=select(rows,[ps[arm]]);both=only_old=only_new=neither=flip=0
                for r in cohort:
                    pid=r['proposition_id'];a=hm[pid][arm]==r['human_gt'];b=ps[arm][pid]==r['human_gt']
                    both+=a and b;only_old+=a and not b;only_new+=b and not a;neither+=not a and not b;flip+=hm[pid][arm]!=ps[arm][pid]
                historical.append(dict(new_model=model,historical_repeat=rep,arm=arm,n=len(cohort),both_correct=both,only_historical_correct=only_old,only_new_correct=only_new,both_wrong=neither,label_flips=flip,net_correct=only_new-only_old))
    for author in ('all','human','llm'):
        full=[r for r in rows if author=='all' or r['author_type']==author]
        for arm in ('B','V_raw','U0','U2'):compare(f'qwen-minus-deepseek/{author}/{arm}',full,preds['deepseek'][arm],preds['qwen'][arm])
    decision={}
    for model in c.MODELS:
        q=[paired[f'{model}/all/U2-minus-{b}']['metrics'][k] for b in ('U0','B') for k in ('percent_agreement','mcc')]
        decision[model]=dict(direction_supported=all(v['delta']>0 for v in q),strong_transfer_evidence=all(v['ci95'][0]>0 for v in q))
    for name,value in [('metrics',allmetrics),('paired',paired),('comparison_cohorts',cohorts),('decision',decision)]:c.put(out/(name+'.json'),value)
    for name,value in [('patients',patients),('transitions',transitions),('historical_comparison',historical),('missing_as_error',sensitivity),('attempt_costs',attempts)]:c.csvwrite(out/(name+'.csv'),value)
    c.put(out/'costs.json',dict(cap_cny=80,attempts=len(attempts),http200=len(term),valid_terminal=sum(x['status'] in c.VALID for x in term.values()),invalid_missing=len(missing),usage_estimate_cny=sum(x['charge_cny'] for x in attempts if x['charge_basis']=='peak_no_cache_usage_estimate'),unknown_reservation_cny=sum(x['charge_cny'] for x in attempts if x['charge_basis']!='peak_no_cache_usage_estimate'),total_occupied_cny=sum(x['charge_cny'] for x in attempts),by_model={m:sum(x['charge_cny'] for x in attempts if x['model_key']==m) for m in c.MODELS},bill_reconciled=False))
    c.put(out/'response_metadata.json',dict(by_model={m:dict(status=dict(Counter(r['status'] for r in norm if r['model_key']==m)),returned_models=dict(Counter(str(r.get('model_returned')) for r in norm if r['model_key']==m)),diagnostics=dict(Counter(x for r in norm if r['model_key']==m for x in r['adherence'])),input_tokens=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in norm if r['model_key']==m),output_tokens=sum((r.get('usage') or {}).get('completion_tokens',0) for r in norm if r['model_key']==m)) for m in c.MODELS}))
    deps=list((c.OUT/'attempts').glob('*/*.json'))+list((c.OUT/'amendment_002').glob('*'))+[c.OUT/'preparation_001/manifest.json',Path(__file__),c.TASK/'core024.py',c.ROOT/'src/verifact_research/evaluation/core.py',c.ROOT/'src/verifact_research/evaluation/metrics.py']
    deps.extend(c.ROOT/f'outputs/020_lambda2_patient_validation/analysis_001/predictions_r{r}.csv' for r in (0,1))
    c.put(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in deps},outputs_sha256={p.name:c.file_hash(p) for p in out.iterdir() if p.is_file()}))
    print(c.canonical(decision))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay-dir');a=p.parse_args();out=c.OUT/'analysis_001'
    if a.replay_dir:
        out=Path(a.replay_dir).resolve();c.require(out.is_relative_to(c.ROOT/'outputs/replays'),'Unsafe replay path')
    run(out)
