"""Synthetic pre-launch tests; never fit or select on actual 029 outcomes."""
import copy,tempfile,unittest
from pathlib import Path
import numpy as np
import common029 as c
import learning029 as l
import evaluate029 as e

def synthetic():
    rows=[];features=[]
    for patient in range(4):
        for j in range(4):
            pid=f'p{patient}_{j}';sid=str(patient);gt=c.LABELS[j%2];group='025' if patient<2 else '026';score=dict(zip(c.LABELS,[30,60,10]));f=c.score_features(score,dict(zip(c.LABELS,[20+10*j,70-10*j,10])))
            f.update({n:float((j+patient)%2) for n in c.REPEAT+c.SEMANTIC+c.QUALITY})
            row=dict(proposition_id=pid,subject_id=sid,author_type='human' if j<2 else 'llm',human_gt=gt,group=group,scores=score,u0=1,u2=0,candidate=True,SD=0 if j%2==0 else 1,repeat=1,trace=1)
            rows.append(row);features.append(dict(row,features=f))
    return rows,features

class Tests(unittest.TestCase):
    def setUp(self):self.config=c.read(c.TASK/'config.json')
    def test_threshold_ties_and_fallback(self):
        x=[dict(probability=p,is_R=True) for p in [.9,.8,.8,.7,.1]];self.assertEqual(l.select_threshold(x),.7);self.assertEqual(l.select_threshold([]),0.)
    def test_strict_outer_exclusion(self):
        _,f=synthetic()
        with self.assertRaises(ValueError):l.fold(f,f[:1],c.SCORE,'Logistic',self.config,['0'])
    def test_holdout_GT_has_no_effect(self):
        _,f=synthetic();tr=[r for r in f if r['subject_id']!='0'];te=[r for r in f if r['subject_id']=='0'];other=copy.deepcopy(te)
        for r in other:r['human_gt']='Not Addressed'
        for model in ('Logistic','XGBoost'):
            a=l.fold(tr,te,c.SCORE,model,self.config,['0']);b=l.fold(tr,other,c.SCORE,model,self.config,['0']);self.assertEqual(a,b)
            for fold in a['inner_folds']:self.assertNotIn('0',fold['training_patients']);self.assertNotIn(fold['held_patient'],fold['training_patients'])
    def test_single_class_and_empty(self):
        _,f=synthetic()
        for model in ('Logistic','XGBoost'):
            for tr,expected in [([],0.5),([r for r in f if r['human_gt']=='Supported'],.9)]:
                p,meta=l.fit(tr,c.SCORE,model,self.config);np.testing.assert_allclose(p(f[:1]),[expected]);self.assertIsNotNone(meta['fallback'])
    def test_feature_whitelist_and_quality_ablation(self):
        schema=c.schema();self.assertEqual(len(c.SCORE),12)
        for condition in ('C_no_quality','D_no_quality'):self.assertTrue(set(c.FEATURES[condition]).isdisjoint(c.QUALITY))
        for forbidden in ('human_gt','subject_id','author_type','group','kind','keep'):self.assertNotIn(forbidden,[x['name'] for x in schema['fields']])
    def test_trace_quality_not_semantic(self):
        repeat=dict(status='valid',verdict='Supported');trace=dict(status='valid',claim_coverage='complete',rows=[dict(relation='supported',claim_spans=[[0,2]],evidence=[dict(valid=True)],diagnostics=[])],adherence=[])
        f=c.new_features(repeat,trace);trace['rows'][0]['evidence'][0]['valid']=False;trace['rows'][0]['diagnostics']=['bad_quote'];q=c.new_features(repeat,trace)
        self.assertEqual([f[n] for n in c.SEMANTIC],[q[n] for n in c.SEMANTIC]);self.assertNotEqual([f[n] for n in c.QUALITY],[q[n] for n in c.QUALITY])
    def test_mapping_preserves_U0(self):
        rows,f=synthetic();rows[0]['candidate']=False;mapping={r['proposition_id']:dict(keep=True) for r in f};p=e.pred_for(rows,mapping);self.assertEqual(p[0],1);self.assertTrue(np.all(p[1:]==0))
    def test_full_synthetic_evaluation(self):
        rows,f=synthetic();config=copy.deepcopy(self.config);config['bootstrap_iterations']=3
        maps={n:{r['proposition_id']:dict(probability=.8 if r['human_gt']=='Supported' else .2,keep=r['human_gt']=='Supported',threshold=.5) for r in f} for n in e.conditions(config)}
        original=c.PREP
        with tempfile.TemporaryDirectory(prefix='verifact029_test_') as d:
            try:
                c.PREP=Path(d)/'prep';c.put(c.PREP/'conflicts.json',{'025':{'mixed_groups':[{'ids':['p0_0','p1_1']}]},'026':{'mixed_groups':[]}})
                e.evaluate(Path(d),'synthetic',rows,maps,config,f,lambda s:None)
                p=Path(d)/'synthetic/evaluation';self.assertTrue((p/'manifest.json').exists());self.assertTrue(c.read(p/'metadata.json')['global_LP_verified']);self.assertEqual(c.read(p/'metrics.json')['pooled/all/A-Logistic']['correct'],16)
            finally:c.PREP=original

if __name__=='__main__':unittest.main()
