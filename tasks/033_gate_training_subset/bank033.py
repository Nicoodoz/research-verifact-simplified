"""Reuse all030 models: unique original-held coverage and one common selection panel."""
from collections import defaultdict,Counter
import numpy as np
import common033 as s

def run():
    out=s.OUT/'historical_001';s.require(not out.exists(),'Historical analysis exists');out.mkdir();allrows=s.lines(s.PREP/'rows_selection_blind.jsonl');original=[r for r in allrows if r['partition']=='original16'];panelrows=[r for r in allrows if r['partition']=='expansion'];features=s.candidate_rows(original);modelindex=s.read(s.HIST/'model_index.json');sourcehash=s.read(s.HIST/'manifest.json')['files'];s.require(len(modelindex)==4356,'All030 models required');before=s.read(s.P31/'before_models/A.json');panel=s.Panel(panelrows,before);oldsubjects={r['subject_id'] for r in original};fsubjects={r['subject_id'] for r in features};groups={r['subject_id']:r['group'] for r in original};unit=s.csvread(s.HIST/'unit_metrics.csv');observed=defaultdict(set)
    for r in unit:observed[r['model_id']].add(r['held_patient'])
    # Max-size030 A OOF, never an in-training baseline for original patients.
    original_A={}
    for sid in sorted(oldsubjects):
        rr=[r for r in original if r['subject_id']==sid];ff=s.candidate_rows(rr);mid=s.old.model_id('A',sorted(fsubjects-{sid}));model=s.read(s.HIST/'models'/f'{mid}.json') if ff else before;pr=s.pred(rr,s.fit_probability(model,ff),model['threshold']);original_A.update({r['proposition_id']:int(p) for r,p in zip(rr,pr)})
    rankings=[];complements=[];patients=[];midlist=[];searchprobs=[];originalprobs=[];setstats={}
    for number,mid in enumerate(sorted(modelindex)):
        path=s.HIST/'models'/f'{mid}.json';s.require(s.sha(path)==sourcehash['models/'+mid+'.json'],'030 model hash '+mid);model=s.read(path);method=model['method'];train=model['final_fit']['training_patients'];setid=mid.split('_',1)[1];s.require(model['final_fit']['features']==s.c.FEATURES[method],'Feature schema');midlist.append(mid)
        if setid not in setstats:setstats[setid]=dict(set_id=setid,train_025=sum(groups[p]=='025' for p in train),train_026=sum(groups[p]=='026' for p in train),**s.training_summary(train,original,features))
        stats=setstats[setid];prob=s.fit_probability(model,panel.candidates);searchprobs.append(prob);m=panel.evaluate(prob,model['threshold']);rankings.append(dict(model_id=mid,method=method,threshold=model['threshold'],observed_test_patients=len(observed[mid]),**stats,**m));pp=s.pred(panelrows,prob,model['threshold'])
        rr=[r for r in original if r['subject_id'] not in train];ff=s.candidate_rows(rr);po=s.fit_probability(model,ff);op=s.pred(rr,po,model['threshold']);vector=np.full(len(features),np.nan);loc={r['proposition_id']:i for i,r in enumerate(features)}
        for r,p in zip(ff,po):vector[loc[r['proposition_id']]]=p
        originalprobs.append(vector);baseline=np.array([original_A[r['proposition_id']] for r in rr]);u2=np.array([r['u2'] for r in rr]);v=s.point(rr,op);complements.append(dict(model_id=mid,set_id=setid,method=method,k=len(train),test_patients=len({r['subject_id'] for r in rr}),test_candidate_patients=len({r['subject_id'] for r in ff}),test_patient_ids=sorted({r['subject_id'] for r in rr}),observed_patient_ids=sorted(observed[mid]),delta_correct_vs_U2=v['correct']-s.point(rr,u2)['correct'],delta_correct_vs_A_OOF=v['correct']-s.point(rr,baseline)['correct'],**v))
        for scope,full,prediction,ref in [('original_complement',rr,op,baseline),('common_search12',panelrows,pp,panel.refpred)]:
            for sid in sorted({r['subject_id'] for r in full}):
                ii=np.array([i for i,r in enumerate(full) if r['subject_id']==sid]);ss=[full[i] for i in ii];pm=s.point(ss,prediction[ii]);bm=s.point(ss,ref[ii]);um=s.point(ss,[r['u2'] for r in ss]);patients.append(dict(model_id=mid,set_id=setid,method=method,k=len(train),scope=scope,subject_id=sid,originally_observed=scope=='original_complement' and sid in observed[mid],delta_correct_vs_reference=pm['correct']-bm['correct'],delta_correct_vs_U2=pm['correct']-um['correct'],**pm))
        if (number+1)%200==0:s.status('reusing030 models',completed=number+1,total=4356)
    s.csvwrite(out/'fixed_set_common_panel_ranking.csv',sorted(rankings,key=lambda r:(r['method'],*s.sort_key(r))));s.put(out/'ranking.json',rankings);s.csvwrite(out/'training_sets.csv',list(setstats.values()));s.csvwrite(out/'original_complement_metrics.csv',complements);s.csvwrite(out/'patient_metrics.csv',patients);s.csvwrite(out/'original_observed_units.csv',unit);s.put(out/'model_ids.json',midlist);np.save(out/'search_probability.npy',np.array(searchprobs),allow_pickle=False);np.save(out/'original_complement_probability.npy',np.array(originalprobs),allow_pickle=False)
    # Whole-sweep records remain a separate table; never relabel as a single training set.
    sweeps=s.read(s.old.PREP/'sweeps.json');sw=[]
    for spec in sweeps:
        if spec['sweep_id']!=spec['canonical_sweep']:continue
        result=s.read(s.HIST/'sweeps'/spec['sweep_id']/'evaluation/result.json')
        for key,value in result['metrics'].items():
            group,author,method=key.split('/');sw.append(dict(sweep_id=spec['sweep_id'],bin=spec['bin'],k=spec['k'],group=group,author=author,method=method,**value))
    s.csvwrite(out/'all141_sweeps.csv',sw);s.put(out/'summary.json',dict(models=4356,fixed_training_sets=len(setstats),canonical_sweeps=141,original_observed_distinct_pairs=sum(len(v) for v in observed.values()),original_observed_repeated_rows=len(unit),original_complement_is_new_offline_coverage=True,shared_search_patients=12,search_claims=998,search_candidates=91,model_fits=0,API_calls=0,confirmation_GT_used=False));s.put(out/'manifest.json',dict(created_utc=s.now(),source=s.sha(s.HIST/'manifest.json'),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()}));s.status('historical bank complete',models=4356,training_sets=len(setstats))

if __name__=='__main__':run()
