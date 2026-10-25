"""Meaningful no-network checks of inherited definitions and036 integration."""
import unittest,copy,json,sys
import numpy as np
import common036 as c
import api036 as api
import predict036 as p
import evaluate036 as ev
from scipy.special import expit

class FinalValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f=c.OUT/'final_freeze_001';cls.models=c.read(f/'models035.json')['models'];cls.standard=c.read(f/'standard_models022.json')['models'];cls.gate=c.read(f/'gate_A.json')
    def test_all_development_inference_matches_original035(self):
        data=c.read(c.ROOT/'outputs/035_lambda_boundary_calibration/run_002/inputs_numeric.json')['main40'];original=p.l.infer(data,self.models)
        for i,r in enumerate(data):
            result=p.infer_scores(dict(zip(c.LABELS,r['scores'])),self.models,self.standard)
            for name,(label,lp) in original.items():
                self.assertEqual(result[name]['label'],int(label[i]));np.testing.assert_allclose(result[name]['logprob'],lp[i],atol=1e-12,rtol=0)
    def test_gate_against_historical_inference(self):
        sys.path.insert(0,str(c.ROOT/'tasks/031_training_expansion_confirmation'))
        from fit_predict031 import infer
        rows=c.lines(c.ROOT/'outputs/033_gate_training_subset/evaluation_001/full_rows.jsonl')
        for r in rows:
            if r['candidate']:
                actual=p.gate(self.gate,r['features']);expected=infer(self.gate,r['features']);self.assertEqual(actual,expected)
    def test_core_and_explanation_duplicates(self):
        for text,valid in [('{"verdict":"Supported","reason":"a","reason":"b","label_scores":{"Supported":70,"Not Supported":20,"Not Addressed":10}}',True),('{"verdict":"Supported","verdict":"Not Supported","label_scores":{"Supported":70,"Not Supported":20,"Not Addressed":10}}',False),('{"verdict":"Supported","label_scores":{"Supported":70,"Not Supported":20,"Not Addressed":11}}',False)]:
            tr=dict(http_status=200,body_text=json.dumps(dict(model=api.api.MODELS['deepseek'],choices=[dict(finish_reason='stop',message=dict(content=text))])))
            original=copy.deepcopy(tr);j=dict(kind='chat',role='score',body=api.body('x','y','score'));got=api.parse(j,tr)
            self.assertEqual(got['status'] in api.api.VALID,valid);self.assertEqual(tr,original)
    def test_zero_floor_and_tie(self):
        s=dict(zip(c.LABELS,[0,50,50]));r=p.infer_scores(s,self.models,self.standard)
        self.assertEqual(r['U0']['label'],1);self.assertEqual(r['U2']['label'],1)
        s=dict(zip(c.LABELS,[50,50,0]));r=p.infer_scores(s,self.models,self.standard)
        self.assertEqual(r['U0']['label'],1);self.assertEqual(r['U2']['label'],0)
    def test_unknown_cost_retained(self):
        j=dict(kind='chat',role='peer',body=api.body('x','y','peer'));self.assertEqual(api.charge(j,dict(http_status=0,body_text=''))[0],api.bound(j))
        tr=dict(http_status=200,body_text=json.dumps(dict(usage=dict(prompt_tokens=400,completion_tokens=200,total_tokens=600))))
        self.assertAlmostEqual(api.charge(j,tr)[0],.0036)
    def test_metric_and_probability_units(self):
        rr=[dict(id=str(i),sid=str(i//2),y=y) for i,y in enumerate([0,0,1,2])];pred=np.array([0,1,0,2]);m=ev.point(rr,pred)
        self.assertEqual(m['correct'],2);self.assertEqual(m['false_S'],1);self.assertEqual(m['PA'],.5);self.assertEqual(m['FSR'],.5)
        self.assertEqual(ev.risk_extra(rr,pred,pred)['ci95'],[0.,0.])
    def test_reserved_blind_materials(self):
        rows=c.lines(c.OUT/'materials_001/inputs.jsonl');self.assertEqual(len(rows),3573)
        self.assertTrue(all(not set(r)&{'GT','human_gt','bhc','source_text','verdict'} for r in rows))
        groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups'];self.assertEqual({r['subject_id'] for r in rows},set(groups['reserved_test']))
if __name__=='__main__':unittest.main()
