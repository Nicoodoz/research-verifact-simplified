"""Execution self-check, not an independent audit. No new model calls."""
import argparse,collections,datetime,math,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
import common026 as c

def run(destination):
    out=Path(destination).resolve();c.require(out.is_relative_to(c.OUT) and not out.exists(),'New026 verification folder required')
    jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);allowed=c.eligible(jobs,'deepseek')+c.eligible(jobs,'qwen')
    checks={}
    def check(name,ok):
        checks[name]=bool(ok);c.require(bool(ok),'Self-check failed: '+name)
    analysis=c.OUT/'analysis_001';manifest=c.read(analysis/'manifest.json')
    check('analysis_dependencies',all(c.sha(c.ROOT/p)==h for p,h in manifest['sha256'].items()))
    check('analysis_outputs',all(c.sha(analysis/p)==h for p,h in manifest['outputs_sha256'].items()))
    check('all_allowed_terminal',set(j['request_id'] for j in allowed)==set(term))
    check('one_attempt_each',len(attempts)==len(term)==len(allowed))
    check('all_core_valid',all(v['status'] in c.VALID for v in term.values()))
    material={r['proposition_id']:r for r in c.lines(c.OUT/'preparation_001/inputs.jsonl')}
    check('same019_evidence',c.sha(c.OUT/'preparation_001/inputs.jsonl')==c.sha(c.ROOT/'outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl'))
    check('same019_cohort',c.sha(c.OUT/'preparation_001/cohort.csv')==c.sha(c.ROOT/'outputs/019_support_boundary_screen/selection/cohort.csv'))
    for j in jobs:
        r=material[j['proposition_id']];body=c.api.old.body(r['text'],r['reference'],j['arm']=='S');body['model']=c.MODELS[j['model_key']]
        check('body_'+j['request_id'],body==j['body'])
    records=[]
    for p in sorted((c.OUT/'attempts').glob('*/request.json')):
        r=c.read(p);receipt=c.read(p.parent/'receipt.json');check('budget_'+r['request_id'],r['prior_task_used_or_reserved_cny']+r['reservation_cny']<=80)
        records.append(r)
    first=min(r['created_utc'] for r in records);gate_time=c.read(c.OUT/'gate_freeze/manifest.json')['created_utc'];prep_time=c.read(c.OUT/'preparation_001/manifest.json')['created_utc'];can=c.read(c.OUT/'candidate_freeze/candidates.json')
    check('gate_and_inputs_frozen_before_first_request',gate_time<first and prep_time<first)
    check('all_D_requests_before_candidate_freeze',max(r['created_utc'] for r in records if r['stage']=='deepseek')<can['created_utc'])
    check('all_Q_after_candidate_freeze',can['created_utc']<min(r['created_utc'] for r in records if r['stage']=='qwen'))
    check('candidate_manifest_contains_all_D_receipts',sum(p.endswith('/receipt.json') for p in c.read(c.OUT/'candidate_freeze/manifest.json')['sha256'])==1300)
    check('cost_below80',sum(a['charge_cny'] for a in attempts)<80)
    check('no_unknown_reserves',all(a['charge_basis']=='peak_no_cache_usage_estimate' for a in attempts))
    qids={j['proposition_id'] for j in allowed if j['model_key']=='qwen'}
    check('Q_exact_candidate_whitelist',qids==set(can['candidate_ids']) and len(qids)==52)
    predictions=c.csvread(analysis/'predictions.csv');predmap={r['proposition_id']:r for r in predictions};cohort=c.csvread(c.OUT/'preparation_001/cohort.csv')
    lookup={(j['proposition_id'],j['model_key'],j['arm']):term.get(j['request_id']) for j in jobs};gate=c.read(c.OUT/'gate_freeze/gate.json');rows=[]
    for r in cohort:
        pid=r['proposition_id'];ds=lookup[pid,'deepseek','S']['scores'];z=[math.log(max(ds[k]/100,1e-6)) for k in c.LABELS]
        dec=lambda lam:0 if z[0]+lam>max(z[1:]) else (1 if z[1]>=z[2] else 2)
        u0,u2=dec(0),dec(2);p=predmap[pid];check('U0_U2_'+pid,p['U0']==c.LABELS[u0] and p['U2']==c.LABELS[u2])
        cand=u0!=0 and u2==0;check('candidate_'+pid,cand==(pid in qids));sd=peer=u0
        if cand:
            qs=lookup[pid,'qwen','S']['scores'];f=c.features(ds,qs);linear=gate['intercept']+sum((f[k]-mean)/scale*coef for k,mean,scale,coef in zip(gate['features'],gate['mean'],gate['scale'],gate['coef']));prob=1/(1+math.exp(-linear));sd=0 if prob>=gate['threshold'] else u0;peer=0 if c.risk.decode(c.risk.logs(qs),2)==0 else u0
        check('SD_peer_'+pid,p['SD']==c.LABELS[sd] and p['peer_U2']==c.LABELS[peer])
        rows.append(dict(r,u0=u0,scores=ds))
    times,gpred=c.frontier.global_states(rows);gr,gf=c.frontier.counts(rows,gpred);summary=c.read(analysis/'summary.json');numeric={}
    for method in ('SD','peer_U2'):
        pred=np.array([c.LABELS.index(predmap[r['proposition_id']][method]) for r in rows]);s=summary[method]
        # Independent linear program over every deterministic lambda state.
        lp=linprog(-gr,A_ub=gf[None,:],b_ub=[s['risk']],A_eq=np.ones((1,len(gr))),b_eq=[1],bounds=(0,None),method='highs')
        check('LP_envelope_'+method,lp.success and abs(-lp.fun-s['global_mixture_R_at_risk'])<1e-8)
        det=max(gr[gf<=s['risk']]);check('deterministic_frontier_'+method,det==s['global_R_at_risk'])
        for item in s['leave_one_patient_out']:
            weights=np.array([float(r['subject_id']!=item['excluded_patient']) for r in rows]);rr,ff=c.frontier.counts(rows,gpred,weights);ar,af=c.frontier.counts(rows,pred,weights)
            lp2=linprog(-rr,A_ub=ff[None,:],b_ub=[af[0]],A_eq=np.ones((1,len(rr))),b_eq=[1],bounds=(0,None),method='highs')
            check('LOO_LP_'+method+'_'+item['excluded_patient'],lp2.success and abs(ar[0]+lp2.fun-item['R_gain_vs_mixture'])<1e-8)
        numeric[method]=dict(global_mixture_R=-lp.fun,mixture_components=[dict(lambda_value=times[i],risk=gf[i],R=gr[i],weight=float(x)) for i,x in enumerate(lp.x) if x>1e-9])
    metrics=c.read(analysis/'metrics.json')
    for author in ('all','human','llm'):
        rs=[r for r in predictions if author=='all' or r['author_type']==author]
        for method in ('U0','U2','SD','peer_U2','B'):
            mm=metrics[author+'/'+('B_common' if method=='B' else method)];cm=[[sum(r['GT']==g and r[method]==p for r in rs) for p in c.LABELS] for g in c.LABELS]
            check('scalar_CM_'+author+method,cm==mm['confusion_matrix'])
            check('correct_'+author+method,sum(cm[i][i] for i in range(3))==mm['correct'])
            if method!='B':
                R=sum(r['U0']!='Supported' and r[method]=='Supported' and r['GT']=='Supported' for r in rs)
                H=sum(r['U0']==r['GT']!='Supported' and r[method]=='Supported' for r in rs)
                W=sum(r['U0'] not in (r['GT'],'Supported') and r['GT']!='Supported' and r[method]=='Supported' for r in rs)
                check('scalar_RHW_'+author+method,(R,H,W)==(mm['R'],mm['H'],mm['W']))
                check('net_is_R_minus_H_'+author+method,mm['correct']-metrics[author+'/U0']['correct']==R-H)
    units=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(c.TASK),'-p','test*.py','-v'],cwd=c.ROOT,text=True,capture_output=True)
    check('unit_tests',units.returncode==0)
    tracked=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();allowed_docs={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'}
    check('no_historical_tracked_changes',set(tracked)<=allowed_docs)
    out.mkdir(parents=True);c.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=sum(checks.values()),checks=checks,numeric=numeric,request_counts=dict(collections.Counter((j['model_key']+'_'+j['arm']) for j in allowed)),parse_status=dict(collections.Counter(v['status'] for v in term.values())),models_returned=dict(collections.Counter(v['model_returned'] for v in term.values())),max_reserved_budget=max(r['prior_task_used_or_reserved_cny']+r['reservation_cny'] for r in records)))
    (out/'unit_tests.txt').write_text(units.stdout+units.stderr,encoding='utf-8')
    c.put(out/'manifest.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [Path(__file__),c.TASK/'test026.py',c.TASK/'test_gate026.py',analysis/'manifest.json',out/'checks.json',out/'unit_tests.txt']}))
    print(c.canonical(dict(self_checks_passed=len(checks),independent_audit=False,numeric=numeric)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
