"""Selection-sealed development OOF comparisons, complete patients and fixed model fits."""
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
import common033 as s
from models033 import Models

def main():
    out=s.OUT/'evaluation_001';s.require(not out.exists(),'Evaluation exists');freeze=s.read(s.OUT/'search_001/selection_freeze.json');s.require(freeze['no_more_search'] and not freeze['confirmation_labels_connected'],'Selection must precede checking');rows=s.lines(s.PREP/'rows_selection_blind.jsonl');path=s.P31/'analysis_001/confirmation_GT.csv';labels={r['proposition_id']:r['human_gt'] for r in s.csvread(path)};out.mkdir();s.put(out/'label_connection.json',dict(created_utc=s.now(),selection_created_utc=freeze['created_utc'],selection_sha256=s.sha(s.OUT/'search_001/selection_freeze.json'),source_sha256=s.sha(path),reserved_used=False))
    for r in rows:
        if r['partition']=='confirmation':r['human_gt']=labels[r['proposition_id']]
    s.require(all(r['human_gt'] in s.LABELS for r in rows),'Complete development labels');split=s.read(s.PREP/'split.json');allpatients=sorted({r['subject_id'] for r in rows});configs={};bank=Models(rows)
    for method in ('A','D'):
        for name,patients in [('historical16',split['original16']),('historical28',split['original16']+split['expansion12']),('all40',allpatients),('historical_best',freeze['historical_best'][method]['train_patients']),('directed_best',freeze['selected'][method]['train_patients'])]:configs[method+'_'+name]=dict(method=method,train_patients=sorted(patients))
    s.put(out/'configurations.json',configs);mappings={};bindings=[];finals={}
    for name,spec in configs.items():
        mapping={}
        for sid in allpatients:
            test=[r for r in rows if r['subject_id']==sid and r['candidate']]
            if not test:bindings.append(dict(configuration=name,held_patient=sid,model_id=None,reason='no candidates; complete patient remains U0'));continue
            allowed=set(spec['train_patients'])-{sid};model,mid=bank.get(spec['method'],allowed);s.require(sid not in model['final_fit']['training_patients'],'OOF patient leakage');prob=s.fit_probability(model,test);mapping.update({r['proposition_id']:dict(subject_id=sid,probability=float(p),threshold=model['threshold'],keep=bool(p>=model['threshold']),model_id=mid) for r,p in zip(test,prob)});bindings.append(dict(configuration=name,held_patient=sid,model_id=mid,training_patients=model['final_fit']['training_patients']))
        mappings[name]=mapping;model,mid=bank.get(spec['method'],spec['train_patients']);finals[name]=dict(model_id=mid,permitted_training_patients=spec['train_patients'],fitted_training_patients=model['final_fit']['training_patients'],threshold=model['threshold'],source=bank.usage[mid]);s.status('development OOF',configuration=name,new_final_models=bank.new)
    bank.save('evaluation_001/model_usage.json');s.put(out/'final_training_models.json',finals);s.put(out/'OOF_model_bindings.json',bindings);s.put(out/'candidate_predictions.json',mappings);s.jsonl(out/'full_rows.jsonl',rows)
    preds={name:s.old.evaluation.pred_for(rows,mp) for name,mp in mappings.items()};preds.update(U0=np.array([r['u0'] for r in rows]),U2=np.array([r['u2'] for r in rows]));metrics={};patients=[];matched={};paired={};curvelist=[];transitions=[];loo=[];bootdraws={}
    comparisons=[(f'{m}_all40',f'{m}_directed_best') for m in ('A','D')]+[(f'{m}_historical28',f'{m}_directed_best') for m in ('A','D')]+[(f'{m}_all40',f'{m}_historical_best') for m in ('A','D')]+[('A_directed_best','D_directed_best')]
    for scope in ('all40','original16','expansion','confirmation'):
        ix=np.array([i for i,r in enumerate(rows) if scope=='all40' or r['partition']==scope]);rr=[rows[i] for i in ix]
        for author in ('all','human','llm'):
            ai=np.array([i for i in ix if author=='all' or rows[i]['author_type']==author]);ss=[rows[i] for i in ai]
            for name,p in preds.items():metrics[scope+'/'+author+'/'+name]=s.point(ss,p[ai])
        for sid in sorted({r['subject_id'] for r in rr}):
            jj=np.array([i for i in ix if rows[i]['subject_id']==sid]);ss=[rows[i] for i in jj]
            for name,p in preds.items():patients.append(dict(scope=scope,subject_id=sid,configuration=name,**s.point(ss,p[jj])))
        times,gp=s.old.frontier.global_states(rr);refs={'global_lambda':gp};params={'global_lambda':times}
        for name,mp in mappings.items():params[name],refs[name]=s.old.evaluation.states(rr,mp)
        for name,pp in refs.items():
            R,F=s.old.frontier.counts(rr,pp)
            curvelist.extend(dict(scope=scope,reference=name,parameter=params[name][j],formal_point=name!='global_lambda' and j==0,R=float(r),risk=float(f)) for j,(r,f) in enumerate(zip(R,F)))
        if scope not in ('all40','confirmation'):continue
        subjects=sorted({r['subject_id'] for r in rr});si=np.array([subjects.index(r['subject_id']) for r in rr]);weights=np.array([np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects)) for seed in range(1000)],float);truth=np.array([r['human_gt']=='Supported' for r in rr]);u0=np.array([r['u0'] for r in rr]);counts={}
        for name,pp in refs.items():
            change=(pp==0)&(u0[None,:]!=0);R=np.array([change[:,si==k]@truth[si==k].astype(float) for k in range(len(subjects))]);F=np.array([change[:,si==k]@(~truth[si==k]).astype(float) for k in range(len(subjects))]);counts[name]=(weights@R,weights@F)
        for base,new in comparisons:
            key=scope+'/'+new+'-minus-'+base;paired[key]=s.old.old.paired_compare(rr,s.old.old.prediction(rr,preds[base][ix]),s.old.old.prediction(rr,preds[new][ix]));transitions.extend(dict(scope=scope,comparison=new+'-minus-'+base,**r) for r in s.old.evaluation.transition(rr,preds[base][ix],preds[new][ix]))
        match_pairs=[(new,base) for base,new in comparisons]+[(f'{m}_{kind}','global_lambda') for m in ('A','D') for kind in ('historical28','all40','historical_best','directed_best')]
        for target,reference in match_pairs:
            R,F=s.old.frontier.counts(rr,refs[reference]);tr,tf=s.old.frontier.counts(rr,preds[target][ix]);value=s.old.frontier.matched(F,R,float(tf[0]),float(tr[0]));lp=linprog(-R,A_ub=F[None,:],b_ub=[tf[0]],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs');s.require(lp.success and abs(tr[0]+lp.fun-value['R_gain_vs_mixture'])<1e-8,'LP verification');d=[];br,bf=counts[reference];ar,af=counts[target]
            for j in range(1000):d.append(s.old.frontier.matched(bf[j],br[j],af[j,0],ar[j,0])['R_gain_vs_mixture'])
            primary=scope=='confirmation' and (target,reference) in [('A_directed_best','A_all40'),('D_directed_best','D_all40')];key=scope+'/'+target+'-vs-'+reference;matched[key]=dict(**value,ci95=np.percentile(d,[2.5,97.5]).tolist(),ci97_5_two_main=np.percentile(d,[1.25,98.75]).tolist() if primary else None);bootdraws[key]=d
            for sid in subjects:
                w=np.array([r['subject_id']!=sid for r in rr],float);R,F=s.old.frontier.counts(rr,refs[reference],w);tr,tf=s.old.frontier.counts(rr,preds[target][ix],w);loo.append(dict(scope=scope,comparison=target+'-vs-'+reference,excluded_patient=sid,**s.old.frontier.matched(F,R,float(tf[0]),float(tr[0]))))
    s.put(out/'metrics.json',metrics);s.csvwrite(out/'metrics.csv',[dict(scope=k.split('/')[0],author=k.split('/')[1],configuration=k.split('/')[2],**v) for k,v in metrics.items()]);s.csvwrite(out/'patients.csv',patients);s.put(out/'paired.json',paired);s.put(out/'matched.json',matched);s.put(out/'bootstrap_draws.json',bootdraws);s.csvwrite(out/'curves.csv',curvelist);s.csvwrite(out/'transitions.csv',transitions);s.csvwrite(out/'leave_one_patient.csv',loo);s.csvwrite(out/'full_predictions.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],partition=r['partition'],author_type=r['author_type'],GT=r['human_gt'],**{name:s.LABELS[int(p[i])] for name,p in preds.items()}) for i,r in enumerate(rows)]);s.put(out/'manifest.json',dict(created_utc=s.now(),selection_sha256=s.sha(s.OUT/'search_001/selection_freeze.json'),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()},all40_selection_optimism=True,confirmation_used_only_after_search=True,bootstrap_refits=False,new_final_fits=bank.new));s.status('evaluation complete',state='evaluated',new_final_fits=bank.new,new_inner_fits=bank.new_inner)

if __name__=='__main__':main()
