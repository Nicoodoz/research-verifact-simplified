"""Synthetic preflight only; do not score actual 030 results before freeze."""
import copy,tempfile,unittest
from pathlib import Path
import numpy as np
import common030 as c
import analyze030 as a

def synthetic():
    groups={str(i):'025' if i<10 else '026' for i in range(15)};rows=[];features=[]
    for sid,g in groups.items():
        for j in range(2):
            score=dict(zip(c.LABELS,[30,60,10]));f=c.v.score_features(score,dict(zip(c.LABELS,[20+40*j,70-40*j,10])));f.update({k:float(j) for k in c.v.REPEAT+c.v.SEMANTIC+c.v.QUALITY})
            r=dict(proposition_id=sid+'_'+str(j),subject_id=sid,author_type='human' if j==0 else 'llm',human_gt='Supported' if (int(sid)+j)%2==0 else 'Not Supported',group=g,scores=score,u0=1,u2=0,candidate=True,SD=1,repeat=1,trace=1)
            rows.append(r);features.append(dict(r,features=f))
    rows.append(dict(proposition_id='zero',subject_id='zero',author_type='human',human_gt='Supported',group='026',scores=dict(zip(c.LABELS,[90,5,5])),u0=0,u2=0,candidate=False,SD=0,repeat=0,trace=0))
    return groups,rows,features

class Tests(unittest.TestCase):
    def setUp(self):self.config=c.read(c.TASK/'config.json')
    def test_deterministic_nested_plan(self):
        groups,_,_=synthetic();ss,uu=c.schedule(groups,self.config);self.assertEqual((ss,uu),c.schedule(groups,self.config));lookup={(u['k'],u['rep'],u['held_patient']):u for u in uu if u['kind']=='size'}
        for rep in range(20):
            for held in groups:
                for k,l in zip(self.config['training_sizes'][:-1],self.config['training_sizes'][1:]):self.assertTrue(set(lookup[k,rep,held]['train_patients'])<=set(lookup[l,rep,held]['train_patients']))
        self.assertEqual(len([s for s in ss if s['bin']=='size_14' and s['sweep_id']==s['canonical_sweep']]),1)
    def test_plan_isolation_and_source_quota(self):
        groups,_,_=synthetic();ss,uu=c.schedule(groups,self.config)
        for u in uu:
            self.assertNotIn(u['held_patient'],u['train_patients']);self.assertEqual(len(u['train_patients']),u['k'])
            if u['kind']=='source':self.assertEqual([u['train_025'],u['train_026']],self.config['source_compositions'][u['bin'].replace('source_','')])
        self.assertEqual(len(ss),160);self.assertEqual(len(uu),2400)
    def test_original_feature_and_config_contract(self):
        cfg=c.read(c.v.PREP/'config.json');schema=c.read(c.v.PREP/'feature_schema.json');self.assertEqual(self.config['methods'],['A','B','D']);self.assertEqual(cfg['logistic']['C'],.1)
        for m in self.config['methods']:self.assertEqual(schema['conditions'][m],c.v.FEATURES[m])
    def test_saved_model_inference_matches_original(self):
        _,_,f=synthetic();train=[r for r in f if r['subject_id'] in ('0','1','2')];test=[r for r in f if r['subject_id']=='3'];cfg=c.read(c.v.PREP/'config.json')
        for m in ('A','B','D'):
            pred,meta=c.learning.fit(train,c.v.FEATURES[m],'Logistic',cfg);np.testing.assert_allclose(pred(test),c.model_probability(meta,test),rtol=0,atol=1e-12)
    def test_nested_model_test_GT_irrelevant(self):
        _,_,f=synthetic();train=[r for r in f if r['subject_id'] in ('0','1','2')];test=[r for r in f if r['subject_id']=='3'];other=copy.deepcopy(test)
        for r in other:r['human_gt']='Not Addressed'
        cfg=c.read(c.v.PREP/'config.json');x=c.learning.fold(train,test,c.v.FEATURES['D'],'Logistic',cfg,['3']);y=c.learning.fold(train,other,c.v.FEATURES['D'],'Logistic',cfg,['3']);self.assertEqual(x,y)
        with self.assertRaises(ValueError):c.learning.fold(train,test,c.v.FEATURES['D'],'Logistic',cfg,['0','3'])
    def test_fallback_and_threshold_tie(self):
        _,_,f=synthetic();cfg=c.read(c.v.PREP/'config.json');tr=[r for r in f if r['human_gt']=='Supported'];pred,meta=c.learning.fit(tr,c.v.FEATURES['D'],'Logistic',cfg);self.assertEqual(meta['fallback'],'single_class');np.testing.assert_allclose(pred(f[:2]),c.model_probability(meta,f[:2]));self.assertEqual(c.learning.select_threshold([dict(probability=p,is_R=True) for p in [.9,.8,.8,.7,.1]]),.7)
    def test_bootstrap_vectorization_matches_scalar_weights(self):
        _,rows,features=synthetic();maps={m:{r['proposition_id']:dict(probability=((i*7+offset)%29)/29,threshold=.4,keep=((i*7+offset)%29)/29>=.4) for i,r in enumerate(features)} for m,offset in [('A',1),('B',4),('D',8)]};result=a.bootstrap_sweep(rows,maps,5);subjects=sorted({r['subject_id'] for r in rows});ix=np.array([subjects.index(r['subject_id']) for r in rows]);_,gp=c.frontier.global_states(rows);refs={'global_lambda':gp}
        for m in ('A','B'):_,refs[m]=c.evaluation.states(rows,maps[m])
        for seed in range(5):
            w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[ix].astype(float);tr,tf=c.frontier.counts(rows,c.evaluation.pred_for(rows,maps['D']),w)
            for ref,pp in refs.items():
                R,F=c.frontier.counts(rows,pp,w);expected=c.frontier.matched(F,R,float(tf[0]),float(tr[0]))['R_gain_vs_mixture'];self.assertAlmostEqual(expected,result['matched_gain'][ref][seed],places=10)
    def test_synthetic_statistics_pipeline(self):
        groups,rows,features=synthetic();cfg=copy.deepcopy(self.config);cfg.update(training_sizes=[3],repetitions=2);sweeps,units=c.schedule(groups,cfg)
        with tempfile.TemporaryDirectory(prefix='verifact030_') as temp:
            run=Path(temp)
            for spec in sweeps:
                if spec['sweep_id']!=spec['canonical_sweep']:continue
                byheld={u['held_patient']:u for u in units if u['sweep_id']==spec['sweep_id']};maps={}
                for m in ('A','B','D'):
                    maps[m]={r['proposition_id']:dict(subject_id=r['subject_id'],probability=.7 if r['human_gt']=='Supported' else .2,threshold=.5,keep=r['human_gt']=='Supported',model_id=c.model_id(m,byheld[r['subject_id']]['train_patients']),train_patients=byheld[r['subject_id']]['train_patients']) for r in features}
                base=run/'sweeps'/spec['sweep_id'];c.put(base/'candidate_predictions.json',maps);a.evaluate_sweep(base/'evaluation',spec,rows,maps)
            a.aggregate(run,sweeps,units,rows,features,lambda x:None,3)
            self.assertTrue((run/'analysis/stability_summary.json').exists());boot=c.read(run/'analysis/conditional_patient_bootstrap.json');self.assertEqual(boot['iterations'],3);self.assertEqual(len(c.csvread(run/'analysis/candidate_stability.csv')),4*3*30)
            st=c.csvread(run/'analysis/source_paired_contrasts.csv');self.assertEqual(len(st),2*3*30*3)

if __name__=='__main__':unittest.main()
