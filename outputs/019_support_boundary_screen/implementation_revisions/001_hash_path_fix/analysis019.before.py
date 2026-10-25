"""Pre-registered selection and complete-cohort analysis; never sends requests."""
from collections import Counter, defaultdict
import argparse, csv, math
import numpy as np
from sklearn.metrics import roc_auc_score
import common019 as c
from verifact_research.evaluation.metrics import classification_metrics

def read_cohort(stage):
    c.check_manifest(c.OUT/stage/'cohort_manifest.json')
    with (c.OUT/stage/'cohort.csv').open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def name(lam): return 'U0' if lam==0 else f'U_lambda_{lam:g}'

def rhw(rows, before, after):
    changes=[i for i,(b,a) in enumerate(zip(before,after)) if b!=a]
    c.require(all(before[i]!='Supported' and after[i]=='Supported' for i in changes),'Not a one-way Supported mapping')
    R=sum(rows[i]['human_gt']=='Supported' for i in changes)
    H=sum(rows[i]['human_gt']==before[i] for i in changes)
    W=len(changes)-R-H
    return dict(changed=len(changes),R=R,H=H,W=W,net_correct=R-H,added_false_s=H+W)

def random_flip(rows, base, counts, seed):
    groups=defaultdict(list)
    for i,(r,p) in enumerate(zip(rows,base)):
        if p!='Supported': groups[(r['subject_id'],r['author_type'],p)].append(i)
    rng=np.random.RandomState(seed); pred=list(base)
    for key,indices in sorted(groups.items()):
        n=counts.get(key,0)
        for i in rng.choice(indices,n,replace=False): pred[i]='Supported'
    return pred

def random_comparison(rows, base, candidate):
    counts=Counter((r['subject_id'],r['author_type'],b) for r,b,a in zip(rows,base,candidate) if b!=a)
    strata={a:[i for i,r in enumerate(rows) if a=='all' or r['author_type']==a] for a in ('all','llm','human')}
    draws={a:[] for a in strata}; actual={}
    for a,ix in strata.items():
        sub=[rows[i] for i in ix]; b=[base[i] for i in ix]; n=[candidate[i] for i in ix]
        actual[a]=dict(rhw(sub,b,n),mcc=classification_metrics([r['human_gt'] for r in sub],n)['mcc'])
    for seed in range(1000):
        p=random_flip(rows,base,counts,seed)
        for a,ix in strata.items():
            sub=[rows[i] for i in ix]; bb=[base[i] for i in ix]; pp=[p[i] for i in ix]
            v=rhw(sub,bb,pp)
            v['mcc']=classification_metrics([r['human_gt'] for r in sub],pp)['mcc']
            draws[a].append(v)
    summary={}
    for a,values in draws.items():
        summary[a]=dict(actual=actual[a],random={k:dict(mean=float(np.mean([v[k] for v in values])),
            p025=float(np.percentile([v[k] for v in values],2.5)),p975=float(np.percentile([v[k] for v in values],97.5)),
            actual_percentile=float(np.mean([v[k]<actual[a][k] for v in values]))) for k in ('net_correct','added_false_s','mcc')},
            note='Conditional matched-count diagnostic, not patient confidence intervals or confirmatory p-values')
    return summary,draws

def protection(rows, base, cand, phase):
    all_b=c.totals(rows,base); all_u=c.totals(rows,cand)
    by={}
    for author in ('llm','human'):
        ix=[i for i,r in enumerate(rows) if r['author_type']==author]
        by[author]=(c.totals([rows[i] for i in ix],[base[i] for i in ix]),c.totals([rows[i] for i in ix],[cand[i] for i in ix]))
    lb,lu=by['llm']; hb,hu=by['human']
    caps=(1,3) if phase=='selection' else (2,3)
    conditions=dict(false_s=all_u['false_s']-all_b['false_s']<=3,
        NS_preserved=all_u['tp']['Not Supported']>=all_b['tp']['Not Supported']-caps[0],
        NA_preserved=all_u['tp']['Not Addressed']>=all_b['tp']['Not Addressed']-caps[1],
        human_nonnegative=hu['correct']>=hb['correct'],llm_false_s=lu['false_s']-lb['false_s']<=1)
    return dict(feasible=all(conditions.values()),conditions=conditions,llm_gain=lu['correct']-lb['correct'],
        human_gain=hu['correct']-hb['correct'],total_gain=all_u['correct']-all_b['correct'],
        false_s_added=all_u['false_s']-all_b['false_s'],llm_correct=lu['correct'],total_correct=all_u['correct'],false_s=all_u['false_s'])

def normalize(stage):
    c.check_manifest(c.OUT/stage/'preparation/manifest.json')
    jobs=c.jsonlines(c.OUT/stage/'preparation/jobs.jsonl'); ledger=c.read(c.OUT/'live_ledger.json')
    progress=ledger['phases'].get(stage,{}).get('jobs',{}); norm=[]
    for j in jobs:
        p=progress.get(j['request_id'],{}); receipt=None
        for ptr in p.get('receipts',[]):
            path=c.OUT/ptr['file']; c.require(c.file_hash(path)==ptr['sha256'],'Changed receipt')
            r=c.read(path)
            c.require(r['job_sha256']==c.fingerprint(j),'Request binding mismatch')
            c.require(r['actual_body_sha256']==c.fingerprint(r['actual_body']),'Actual body digest mismatch')
            expected=dict(j['body']); expected['model']=r['actual_body']['model']
            c.require(expected==r['actual_body'],'Body changed beyond provider model ID')
            if r['transport']['http_status']==200:
                c.require(receipt is None,'Multiple HTTP200 answers for one request'); receipt=r
        parsed=c.parse(receipt['transport'],j['arm']=='S') if receipt else dict(status='missing',verdict=None,scores=None,errors=['no_answer'])
        norm.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],arm=j['arm'],repeat=j['repeat'],
            provider=receipt['provider'] if receipt else None,account=receipt['account'] if receipt else None,**parsed))
    return norm

def analyze(stage):
    norm=normalize(stage); folder=c.OUT/stage/'analysis_001'; folder.mkdir(parents=True,exist_ok=False)
    c.write_lines(folder/'normalized.jsonl',norm)
    bad=[r for r in norm if r['status']!='success']
    if stage=='probe':
        result=dict(passed=not bad and len(norm)==12,requests=len(norm),invalid=len(bad),invalid_requests=[r['request_id'] for r in bad])
        c.write_json(c.OUT/'probe_check.json',result); print(c.canonical(result)); return
    if bad:
        result=dict(passed=False,status='measurement_or_execution_blocked',invalid_or_missing=len(bad),total=len(norm),reason='No available-case primary analysis')
        c.write_json(folder/'blocked.json',result); print(c.canonical(result)); return
    rows=read_cohort(stage)
    with (c.OUT/stage/'preparation/assignments.csv').open(encoding='utf-8-sig',newline='') as f: assignments=list(csv.DictReader(f))
    lookup={r['request_id']:r for r in norm}; logical={(r['proposition_id'],r['arm'],int(r['repeat'])):lookup[r['request_id']] for r in assignments}
    rounds=range(2) if stage=='validation' else range(1)
    grids=[]; all_metrics={}; all_paired={}; scores_diag={}; transitions=[]; patient_rows=[]; repeat_preds={}
    for rep in rounds:
        B=[logical[(r['proposition_id'],'B',rep)]['verdict'] for r in rows]
        S=[logical[(r['proposition_id'],'S',rep)] for r in rows]
        preds={'B':B,'V_raw':[x['verdict'] for x in S],**{name(l):[c.decision(x['scores'],l) for x in S] for l in c.GRID},
            'O':[r['O'] for r in rows],'C_history':[r['C'] for r in rows],'Always_S':['Supported']*len(rows)}
        repeat_preds[rep]=preds
        c.write_csv(folder/f'predictions_r{rep}.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],**{k:p[i] for k,p in preds.items()}) for i,r in enumerate(rows)])
        for arm,labels in preds.items():
            for author in ('llm','human','all'):
                ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author]
                sub=[rows[i] for i in ix]; values=[labels[i] for i in ix]
                key=f'r{rep}/{author}/{arm}'
                all_metrics[key]=c.evaluate(sub,c.prediction_rows(sub,values))
                all_metrics[key]['counts']=c.totals(sub,values)
                if arm not in ('B','O','C_history','Always_S'):
                    for base_arm in ('B','U0'):
                        before=[preds[base_arm][i] for i in ix]
                        all_paired[key+'/minus_'+base_arm]=c.paired_compare(sub,c.prediction_rows(sub,before),c.prediction_rows(sub,values))
            for sid in sorted({r['subject_id'] for r in rows}):
                ix=[i for i,r in enumerate(rows) if r['subject_id']==sid]
                patient_rows.append(dict(repeat=rep,arm=arm,subject_id=sid,**c.totals([rows[i] for i in ix],[labels[i] for i in ix])))
        for lam in c.GRID:
            lab=preds[name(lam)]
            g=dict(repeat=rep,lambda_value=lam,**protection(rows,B,lab,stage),**{'boundary_'+k:v for k,v in rhw(rows,preds['U0'],lab).items()})
            grids.append(g)
            random_summary,random_draws=random_comparison(rows,preds['U0'],lab)
            c.write_json(folder/f'random_r{rep}_lambda{lam:g}.json',random_summary)
            c.write_lines(folder/f'random_draws_r{rep}_lambda{lam:g}.jsonl',[dict(author=a,seed=i,**v) for a,vs in random_draws.items() for i,v in enumerate(vs)])
            for i,r in enumerate(rows):
                if B[i]!=lab[i] or preds['U0'][i]!=lab[i]:
                    transitions.append(dict(repeat=rep,lambda_value=lam,proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],B=B[i],U0=preds['U0'][i],candidate=lab[i]))
        for author in ('llm','human','all'):
            ix=[i for i,r in enumerate(rows) if (author=='all' or r['author_type']==author) and B[i]!='Supported']
            y=[int(rows[i]['human_gt']=='Supported') for i in ix]
            margins=[math.log(max(S[i]['scores']['Supported']/100,1e-6))-max(math.log(max(S[i]['scores'][k]/100,1e-6)) for k in c.LABELS[1:]) for i in ix]
            scores_diag[f'r{rep}/{author}']=dict(B_rejected_n=len(ix),true_S=sum(y),auc=float(roc_auc_score(y,margins)) if len(set(y))==2 else None)
        scores_diag[f'r{rep}/distribution']=dict(verdict_argmax_disagreement=sum(a!=b for a,b in zip(preds['V_raw'],preds['U0'])),
            any_zero=sum(0 in x['scores'].values() for x in S),ties=sum(list(x['scores'].values()).count(max(x['scores'].values()))>1 for x in S),
            Supported_score_histogram=dict(Counter(x['scores']['Supported'] for x in S)))
    c.write_json(folder/'metrics.json',all_metrics);c.write_json(folder/'paired.json',all_paired)
    c.write_json(folder/'score_diagnostics.json',scores_diag);c.write_csv(folder/'thresholds.csv',grids)
    c.write_csv(folder/'transitions.csv',transitions);c.write_csv(folder/'patients.csv',patient_rows)
    if stage=='selection':
        feasible=[g for g in grids if g['feasible']]
        best=max(feasible,key=lambda g:(g['llm_correct'],g['total_correct'],-g['false_s'],-g['lambda_value'])) if feasible else None
        gate=dict(created_utc=c.now(),passed=bool(best and best['llm_gain']>=5 and best['total_gain']>=13),selected_lambda=best['lambda_value'] if best else None,
            chosen=best,status='completed_selection',rule='LLM_correct,total_correct,-false_s,-lambda; protection first; gain >=5/13',
            fitting_cohort='010_only_650',validation_GT_used_for_selection=False,source_jobs_sha256=c.file_hash(c.OUT/stage/'preparation/jobs.jsonl'),analysis_code_sha256=c.file_hash(__file__))
        c.write_json(c.OUT/'selection_freeze.json',gate)
    else:
        lam=c.read(c.OUT/'selection_freeze.json')['selected_lambda']; chosen=[g for g in grids if g['lambda_value']==lam]
        gains=defaultdict(list)
        for rep in rounds:
            for sid in sorted({r['subject_id'] for r in rows}):
                ix=[i for i,r in enumerate(rows) if r['subject_id']==sid]
                gains[sid].append(sum(rows[i]['human_gt']==repeat_preds[rep][name(lam)][i] for i in ix)-sum(rows[i]['human_gt']==repeat_preds[rep]['B'][i] for i in ix))
        passed=all(g['feasible'] and g['llm_gain']>=4 and g['total_gain']>=13 for g in chosen) and sum(np.mean(v)>0 for v in gains.values())>=4
        mcc_drop=any(all_metrics[f'r{rep}/{a}/{name(lam)}']['mcc']<all_metrics[f'r{rep}/{a}/B']['mcc'] for rep in rounds for a in ('llm','human'))
        stable=Counter()
        for i,r in enumerate(rows):
            bb=[repeat_preds[t]['B'][i] for t in rounds]; uu=[repeat_preds[t][name(lam)][i] for t in rounds]
            providers={logical[(r['proposition_id'],a,t)]['provider'] for t in rounds for a in ('B','S')}
            if len(providers)>1: stable['cross_provider_unavailable']+=1;continue
            if bb[0]!=bb[1]:stable['B_flip']+=1
            if uu[0]!=uu[1]:stable['candidate_flip']+=1
            if bb[0]==bb[1]!='Supported' and r['human_gt']=='Supported' and uu==['Supported']*2:stable['stable_S_rescue']+=1
            if bb[0]==bb[1]==r['human_gt']!='Supported' and uu==['Supported']*2:stable['stable_falseS_harm']+=1
        gate=dict(passed=bool(passed),MCC_tradeoff=bool(mcc_drop),new_patient_confirmation_automatically_authorized=False,
            selected_lambda=lam,rounds=chosen,patient_gains=dict(gains),stability=dict(stable),
            boundary_extra_gain_both_rounds=bool(lam>0 and all(g['boundary_net_correct']>0 for g in chosen)))
        c.write_json(c.OUT/'validation_decision.json',gate)
    c.write_json(folder/'decision.json',gate)
    c.write_json(folder/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in folder.iterdir() if p.is_file()}))
    print(c.canonical(gate),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['probe','selection','validation']);a=p.parse_args();analyze(a.stage)
