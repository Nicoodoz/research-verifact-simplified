"""Frozen026 inference, complete-case002 evaluation and full global-lambda reference."""
import argparse
from collections import Counter
from pathlib import Path
import numpy as np
import common026 as c
def metric(rows,pred):
    m=c.risk.evaluate(rows,c.risk.prediction(rows,pred),profile='none');gt=np.array([c.LABELS.index(r['human_gt']) for r in rows]);u0=np.array([r['u0'] for r in rows]);p=np.asarray(pred);chg=(u0!=0)&(p==0)
    R=int(sum(chg&(gt==0)));H=int(sum(chg&(gt!=0)&(u0==gt)));W=int(sum(chg&(gt!=0)&(u0!=gt)))
    return dict(n=len(rows),correct=int(sum(gt==p)),PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],R=R,H=H,W=W,risk=H+W,false_S=int(sum((gt!=0)&(p==0))),S_recall=m['per_class'][c.LABELS[0]]['recall'],NS_recall=m['per_class'][c.LABELS[1]]['recall'],NA_recall=m['per_class'][c.LABELS[2]]['recall'],confusion_matrix=m['confusion_matrix'])
def run(out):
    c.require(not (c.OUT/'live.lock').exists(),'API active');jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);counts=Counter(x['request_id'] for x in attempts)
    scheduled=c.eligible(jobs,'deepseek')+c.eligible(jobs,'qwen');c.require(all(j['request_id'] in term or counts[j['request_id']]>=3 for j in scheduled),'Unfinished eligible requests')
    c.require(sum(x['charge_cny'] for x in attempts)<=80,'Over budget')
    rows=c.csvread(c.OUT/'preparation_001/cohort.csv');gate=c.read(c.OUT/'gate_freeze/gate.json');ids=set(c.read(c.OUT/'candidate_freeze/candidates.json')['candidate_ids']);logical={(j['proposition_id'],j['model_key'],j['arm']):term.get(j['request_id']) for j in jobs}
    prepared=[];excluded=[];allpred=[];gate_records=[]
    for r in rows:
        pid=r['proposition_id'];d=logical[(pid,'deepseek','S')];b=logical[(pid,'deepseek','B')];q=logical[(pid,'qwen','S')]
        bvalid=b and b['status'] in c.VALID
        if not d or d['status'] not in c.VALID:
            excluded.append(dict(proposition_id=pid,reason='invalid_or_missing_D_score'));allpred.append(dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],U0=None,U2=None,SD=None,peer_U2=None,B=b['verdict'] if bvalid else None,SD_fail_closed=None));continue
        u0=int(c.risk.decode(c.risk.logs(d['scores']),0));u2=int(c.risk.decode(c.risk.logs(d['scores']),2));candidate=u0!=0 and u2==0;c.require(candidate==(pid in ids),'Candidate definition differs')
        valid_q=bool(q and q['status'] in c.VALID);sd=peer=u0;prob=None
        if candidate:
            if valid_q:
                v=c.infer(gate,d['scores'],q['scores']);prob=v['prob'];sd=0 if v['keep'] else u0;peer=0 if int(c.risk.decode(c.risk.logs(q['scores']),2))==0 else u0
                gate_records.append(dict(proposition_id=pid,subject_id=r['subject_id'],prob=prob,threshold=v['threshold'],keep=v['keep'],features=c.features(d['scores'],q['scores'])))
            else:sd=peer=None;excluded.append(dict(proposition_id=pid,reason='candidate_Q_score_invalid_or_missing'))
        rr=dict(r,u0=u0,u2=u2,scores=d['scores'],candidate=candidate,SD=sd,peer_U2=peer,B=c.LABELS.index(b['verdict']) if bvalid else None,SD_fail_closed=u0 if sd is None else sd)
        prepared.append(rr);allpred.append(dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],U0=c.LABELS[u0],U2=c.LABELS[u2],SD=c.LABELS[sd] if sd is not None else None,peer_U2=c.LABELS[peer] if peer is not None else None,B=b['verdict'] if bvalid else None,SD_fail_closed=c.LABELS[rr['SD_fail_closed']]))
    main=[r for r in prepared if r['SD'] is not None];c.require(bool(main),'Empty primary cohort');out.mkdir(parents=True,exist_ok=False)
    c.csvwrite(out/'predictions.csv',allpred);c.put(out/'gate_inference.json',gate_records);c.put(out/'excluded.json',excluded)
    c.put(out/'coverage.json',dict(frozen_n=650,D_score_n=len(prepared),primary_n=len(main),D_score_ids=[r['proposition_id'] for r in prepared],primary_ids=[r['proposition_id'] for r in main],excluded=excluded,candidate_n=len(ids),gate_evaluated_candidates=len(gate_records),primary_cohort_sha256=c.fingerprint([[r['proposition_id'],r['subject_id'],r['human_gt']] for r in main])))
    preds={'U0':np.array([r['u0'] for r in main]),'U2':np.array([r['u2'] for r in main]),'SD':np.array([r['SD'] for r in main]),'peer_U2':np.array([r['peer_U2'] for r in main])};metrics={};paired={};patients=[];curves=[];transitions=[];summary={}
    times,gpred=c.frontier.global_states(main);gr,gf=c.frontier.counts(main,gpred)
    for author in ('all','human','llm'):
        ix=[i for i,r in enumerate(main) if author=='all' or r['author_type']==author];rr=[main[i] for i in ix]
        for name,p in preds.items():metrics[author+'/'+name]=metric(rr,p[ix])
        for cand,base in [('SD','U0'),('SD','U2'),('peer_U2','U2')]:paired[author+'/'+cand+'-minus-'+base]=c.risk.paired_compare(rr,c.risk.prediction(rr,preds[base][ix]),c.risk.prediction(rr,preds[cand][ix]))
        bb=[r for r in main if r['B'] is not None and (author=='all' or r['author_type']==author)]
        if bb:
            metrics[author+'/B_common']=metric(bb,[r['B'] for r in bb]);metrics[author+'/B_common'].update(R=None,H=None,W=None,risk=None,lambda_transition_counts_applicable=False)
            metrics[author+'/SD_B_common']=metric(bb,[r['SD'] for r in bb]);paired[author+'/SD-minus-B']=c.risk.paired_compare(bb,c.risk.prediction(bb,[r['B'] for r in bb]),c.risk.prediction(bb,[r['SD'] for r in bb]))
        for lam,p in zip(times,gpred):curves.append(dict(scope='primary_common',author=author,lambda_value=lam,**metric(rr,p[ix])))
    fulltimes,fullgpred=c.frontier.global_states(prepared)
    for lam,p in zip(fulltimes,fullgpred):curves.append(dict(scope='D_score_valid',author='all',lambda_value=lam,**metric(prepared,p)))
    for sid in sorted(set(r['subject_id'] for r in main)):
        ix=[i for i,r in enumerate(main) if r['subject_id']==sid]
        for name,p in preds.items():patients.append(dict(subject_id=sid,method=name,**metric([main[i] for i in ix],p[ix])))
    for i,r in enumerate(main):
        for name in ('U2','SD','peer_U2'):
            p=preds[name][i];g=c.LABELS.index(r['human_gt']);u0=r['u0'];kind='R' if u0!=0 and p==0 and g==0 else 'H' if u0==g!=0 and p==0 else 'W' if g!=0 and u0 not in (g,0) and p==0 else ''
            transitions.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],method=name,U0=c.LABELS[u0],prediction=c.LABELS[int(p)],RHW=kind))
    subjects=sorted(set(r['subject_id'] for r in main));subindex=np.array([subjects.index(r['subject_id']) for r in main]);u2=metrics['all/U2']
    for name in ('SD','peer_U2'):
        pt=metrics['all/'+name];mm=c.frontier.matched(gf,gr,pt['risk'],pt['R']);draw=[];loo=[]
        for seed in range(1000):
            w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[subindex];ar,af=c.frontier.counts(main,preds[name],w);rr,ff=c.frontier.counts(main,gpred,w);v=c.frontier.matched(ff,rr,af[0],ar[0]);draw.append([v['R_gain_vs_global'],v['R_gain_vs_mixture']])
        for sid in subjects:
            w=np.array([r['subject_id']!=sid for r in main],dtype=float);ar,af=c.frontier.counts(main,preds[name],w);rr,ff=c.frontier.counts(main,gpred,w);loo.append(dict(excluded_patient=sid,**c.frontier.matched(ff,rr,af[0],ar[0])))
        ci=np.percentile(draw,[2.5,97.5],axis=0)
        summary[name]=dict(**pt,**mm,rescue_retention=pt['R']/u2['R'] if u2['R'] else None,risk_retention=pt['risk']/u2['risk'] if u2['risk'] else None,deterministic_gain_ci95=ci[:,0].tolist(),mixture_gain_ci95=ci[:,1].tolist(),leave_one_patient_out=loo)
    s=summary['SD'];checks=dict(rescue80=s['rescue_retention'] is not None and s['rescue_retention']>=.8,risk75=s['risk_retention'] is not None and s['risk_retention']<=.75,det_gain5=s['R_gain_vs_global']>=5,mix_gain3=s['R_gain_vs_mixture']>=3,loo5=sum(v['R_gain_vs_mixture']>0 for v in s['leave_one_patient_out'])>=5,authors_net_nonnegative=all(metrics[a+'/SD']['correct']>=metrics[a+'/U0']['correct'] for a in ('human','llm')));point_support=all(checks.values())
    c.put(out/'decision.json',dict(checks={k:bool(v) for k,v in checks.items()},point_transfer_support=bool(point_support),clear_transfer_support=bool(point_support and s['mixture_gain_ci95'][0]>0),fixed_gate_unchanged=True,no_retraining=True))
    sensitivity={name:dict(valid_n=sum(r[name] in c.LABELS for r in allpred),correct=sum(r[name]==r['GT'] for r in allpred),missing_as_error_PA=sum(r[name]==r['GT'] for r in allpred)/650) for name in ('B','U0','U2','SD','peer_U2','SD_fail_closed')}
    c.put(out/'metrics.json',metrics);c.put(out/'paired.json',paired);c.put(out/'summary.json',summary);c.put(out/'missing_sensitivity.json',sensitivity)
    c.csvwrite(out/'global_frontier.csv',curves);c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'transitions.csv',transitions);c.csvwrite(out/'cost_ledger.csv',attempts)
    c.put(out/'costs.json',dict(cap_cny=80,attempts=len(attempts),http200=len(term),usage_estimate_cny=sum(x['charge_cny'] for x in attempts if x['charge_basis']=='peak_no_cache_usage_estimate'),unknown_reservation_cny=sum(x['charge_cny'] for x in attempts if x['charge_basis']!='peak_no_cache_usage_estimate'),total_occupied_cny=sum(x['charge_cny'] for x in attempts),by_model={m:sum(x['charge_cny'] for x in attempts if x['model_key']==m) for m in c.MODELS}))
    normalized=[dict(request_id=j['request_id'],proposition_id=j['proposition_id'],model_key=j['model_key'],arm=j['arm'],**term.get(j['request_id'],dict(status='invalid_core_fields',errors=['no_HTTP200_after_attempts']))) for j in scheduled]
    with (out/'normalized.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in normalized:f.write(c.canonical(r)+'\n')
    deps=[c.OUT/'gate_freeze/manifest.json',c.OUT/'preparation_001/manifest.json',c.OUT/'candidate_freeze/manifest.json',Path(__file__),c.TASK/'common026.py']+list((c.OUT/'attempts').glob('*/*.json'))
    c.put(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},outputs_sha256={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
    print(c.canonical(c.read(out/'decision.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay-dir');a=p.parse_args();out=Path(a.replay_dir).resolve() if a.replay_dir else c.OUT/'analysis_001';c.require(out==c.OUT/'analysis_001' or out.is_relative_to(c.ROOT/'outputs/replays'),'Unsafe replay output');run(out)
