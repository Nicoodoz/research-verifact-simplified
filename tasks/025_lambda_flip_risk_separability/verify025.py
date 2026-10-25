"""Independent scalar counts, LP envelope, patient isolation and frozen-source checks."""
import math,socket
from collections import Counter
import numpy as np
from scipy.optimize import linprog
import common025 as c
import frontier025_numeric as f
def run():
    a=c.OUT/'analysis_003';rows=c.jl(c.OUT/'preparation_001/rows.jsonl');groups={g:[r for r in rows if r['group']==g] for g in set(r['group'] for r in rows)}
    for path,h in c.read(c.OUT/'preparation_001/source_manifest.json')['sha256'].items():c.require(c.sha(c.ROOT/path)==h,'Source changed: '+path)
    for path,h in c.read(c.OUT/'execution_plan.json')['code_before_first_study_fit'].items():c.require(c.sha(c.ROOT/path)==h,'Original preregistered code changed')
    manifest=c.read(a/'manifest.json')
    for path,h in manifest['dependencies'].items():c.require(c.sha(c.ROOT/path)==h,'Formal dependency changed')
    for name,h in manifest['outputs'].items():c.require(c.sha(a/name)==h,'Formal output changed')
    fitted=c.read(a/'fit_audit.json');pred_oof={(r['group'],r['method'],r['proposition_id']):r for r in c.csvrows(a/'candidate_oof.csv')};nfit=0
    for fit in fitted:
        training={r['proposition_id']:r for r in groups[fit['train_group']]};used=[training[i] for i in fit['training_ids']]
        c.require(all(r['candidate'] for r in used),'Noncandidate used in fit')
        c.require(sorted(set(r['subject_id'] for r in used))==fit['training_patients'],'Train identity mismatch')
        held=fit['held_patient'];c.require(held not in fit['training_patients'],'Outer patient leakage')
        if held=='external_cohort':c.require(set(fit['training_patients']).isdisjoint(r['subject_id'] for r in groups[fit['group']]),'Cross-cohort leakage')
        for inner in fit['inner_folds']:c.require(inner['held_patient'] not in inner['training_patients'] and held not in inner['training_patients'],'Inner patient leakage')
        x=np.array([[r['features'][n] for n in fit['features']] for r in used]);np.testing.assert_allclose(np.mean(x,axis=0),fit['mean'],atol=1e-12)
        for r in groups[fit['group']]:
            key=(fit['group'],fit['method'],r['proposition_id'])
            if r['subject_id']==held and key in pred_oof and not fit['constant_fallback']:
                v=np.array([r['features'][n] for n in fit['features']]);z=float(((v-np.array(fit['mean']))/np.array(fit['scale']))@np.array(fit['coef'])+fit['intercept']);p=1/(1+math.exp(-z))
                c.require(abs(p-float(pred_oof[key]['prob']))<1e-10,'OOF probability differs from frozen model')
        nfit+=1
    mm=c.csvrows(a/'full_metrics.csv');summary=c.read(a/'summary.json');checks=0
    for group,rr in groups.items():
        pp={r['proposition_id']:r for r in c.csvrows(a/f'predictions_{group}.csv')};gc=[r for r in c.csvrows(a/'global_lambda_curves.csv') if r['group']==group and r['author']=='all'];globalR=np.array([float(r['R']) for r in gc]);globalF=np.array([float(r['risk']) for r in gc])
        for method in pp[next(iter(pp))]:
            if method in ('group','proposition_id','subject_id','author_type','human_gt'):continue
            pred=[c.LABELS.index(pp[r['proposition_id']][method]) for r in rr]
            R=H=W=0
            for r,p in zip(rr,pred):
                if p!=r['u0']:
                    c.require(r['candidate'] and p==0,'Illegal gate change')
                    if r['human_gt']=='Supported':R+=1
                    elif c.LABELS[r['u0']]==r['human_gt']:H+=1
                    else:W+=1
            saved=next(x for x in mm if x['group']==group and x['method']==method and x['author']=='all')
            c.require((R,H,W)==tuple(int(saved[k]) for k in ('R','H','W')),'RHW scalar mismatch')
            exact=c.evaluate(rr,c.prediction(rr,pred),profile='none')
            c.require(abs(exact['percent_agreement']-float(saved['PA']))<1e-12 and abs(exact['mcc']-float(saved['MCC']))<1e-12,'002 metric mismatch');checks+=1
            if method in summary[group]:
                lp=linprog(-globalR,A_ub=globalF[None,:],b_ub=[H+W],A_eq=np.ones((1,len(gc))),b_eq=[1.],bounds=(0,None),method='highs')
                c.require(lp.success,'LP failure');c.require(abs(-lp.fun-summary[group][method]['global_mixture_R_at_risk'])<1e-7,'Convex frontier not optimal')
                for loo in summary[group][method]['leave_one_patient_out']:
                    excluded=loo['excluded_patient'];ar=sum(r['subject_id']!=excluded and r['human_gt']=='Supported' and r['u0']!=p==0 for r,p in zip(rr,pred));af=sum(r['subject_id']!=excluded and r['human_gt']!='Supported' and r['u0']!=p==0 for r,p in zip(rr,pred))
                    gr=[];gf=[]
                    for state in gc:
                        lam=float(state['lambda_value']);xR=xF=0
                        for r in rr:
                            if r['subject_id']==excluded:continue
                            score=r['scores'];q=max((1,2,0),key=lambda k:math.log(max(score[c.LABELS[k]]/100,1e-6))+(lam if k==0 else 0))
                            if r['u0']!=q==0:
                                if r['human_gt']=='Supported':xR+=1
                                else:xF+=1
                        gr.append(xR);gf.append(xF)
                    independent=f.matched(gf,gr,af,ar)
                    c.require(abs(independent['R_gain_vs_mixture']-loo['R_gain_vs_mixture'])<1e-9,'LOO scalar mismatch')
    unchanged=[]
    for p in (c.OUT/'analysis_002').iterdir():
        if p.is_file() and p.name not in ('summary.json','decision.json','manifest.json'):
            c.require(c.sha(p)==c.sha(a/p.name),'Numerical repair changed other output: '+p.name);unchanged.append(p.name)
    print(c.canonical(dict(outer_fits_verified=nfit,full_prediction_metrics_verified=checks,LP_envelopes_and_scalar_LOO_verified=True,unchanged_after_count_fix=unchanged,new_API_calls=0)))
if __name__=='__main__':
    socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('025 network prohibited'))
    run()
