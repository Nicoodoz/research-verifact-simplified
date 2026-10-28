"""CPU numerical and orchestration checks; no model stack, clinical text or API."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import common106 as c
from objectives106 import (softmax,normalized_weights,ideal_weighted_posterior,
    exact_legal_label_probabilities,ce_loss_gradient,false_s_loss_gradient,finite_difference,LABELS)
from run106 import verify_bundle,verify_authorization,used_cny,require_budget,watch

class CPUChecks(unittest.TestCase):
    def test_class_weight_normalization_and_decision_boundary(self):
        labels=['Supported']*320+['Not Supported']*96+['Not Addressed']*96
        w=normalized_weights(labels,dict(zip(LABELS,[1.,2.,2.])))
        self.assertAlmostEqual(w.mean(),1.)
        self.assertAlmostEqual(w[320]/w[0],2.)
        # Higher non-S weights can change the population argmax without any
        # extra information about reference evidence. Not a clinical result.
        p=np.array([.5,.3,.2]);q=ideal_weighted_posterior(p,[1,2,2])
        self.assertEqual(int(p.argmax()),0);self.assertEqual(int(q.argmax()),1)
        self.assertAlmostEqual(q[1]/q[2],p[1]/p[2])

    def test_cost_gradient_exact_classes_no_supported_substring(self):
        logits=np.array([.3,-.4,.2])
        for target in range(3):
            loss,grad=false_s_loss_gradient(logits,target,.7)
            numerical=finite_difference(lambda z:false_s_loss_gradient(z,target,.7)[0],logits)
            np.testing.assert_allclose(grad,numerical,rtol=1e-6,atol=1e-8)
            self.assertAlmostEqual(grad.sum(),0.)
            base,base_grad=ce_loss_gradient(logits,target)
            if target==0:np.testing.assert_array_equal(grad,base_grad);self.assertEqual(loss,base)
            else:self.assertGreater(grad[0],base_grad[0])
        self.assertEqual(LABELS[1],'Not Supported')
        # Both true NS and NA are non-S; neither is confused with S merely
        # because its label spelling contains the word Supported.
        np.testing.assert_allclose(false_s_loss_gradient(logits,1,.7)[1]-ce_loss_gradient(logits,1)[1],
                                   false_s_loss_gradient(logits,2,.7)[1]-ce_loss_gradient(logits,2)[1])

    def test_complete_legal_paths_not_single_token_score(self):
        scores={'Supported':[-.2,-.4,-.1],'Not Supported':[-.2,-.3,-1.2,-.1],'Not Addressed':[-.2,-.3,-.2,-.1]}
        q=exact_legal_label_probabilities(scores)
        np.testing.assert_allclose(q,softmax([sum(scores[k]) for k in LABELS]))
        self.assertGreater(q[2],q[1])
        with self.assertRaises(ValueError):exact_legal_label_probabilities({'Supported':[-.1]})
        # A locally greedy Not branch may beat S while its two complete leaves
        # each lose to S. Restricted-path MAP is therefore a diagnostic only.
        q=np.array([.4,.3,.3]);greedy='Not Supported' if q[1]+q[2]>q[0] else 'Supported'
        self.assertEqual(LABELS[int(q.argmax())],'Supported');self.assertNotEqual(greedy,LABELS[int(q.argmax())])

    def test_whole_run_budget_gate_before_optimizer(self):
        import platform
        from run106 import require_whole_remaining
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger=root/'compute106.json'
            c.put(ledger,dict(operating_line_cny=18,closed_sessions=[],active=dict(machine=platform.node(),hourly_cny=8.,billing_start_epoch=1000.)))
            with patch('run106.time.time',return_value=1000.):
                result=require_whole_remaining(ledger,dict(remaining_after_gate_seconds=8000,baseline_rerun_extra_seconds=1200),'reuse')
                self.assertTrue(result['fits_complete_frozen_run'])
                with self.assertRaises(TimeoutError):require_whole_remaining(ledger,dict(remaining_after_gate_seconds=8000,baseline_rerun_extra_seconds=1200),'rerun')
            self.assertEqual(c.read(root/'whole_run_budget_gate.json')['optimizer_updates'],0)

    def test_diagnostic_probability_nan_mismatch_and_map_rejected(self):
        from copy import deepcopy
        from evaluate106 import validate_path_score
        score=dict(complete_JSON_EOS_sum_logP={label:float(np.log(p)) for label,p in zip(LABELS,[.4,.3,.3])},
                   restricted_legal_q=dict(zip(LABELS,[.4,.3,.3])),restricted_legal_MAP='Supported',
                   first_value_branch_raw_full_vocab_probabilities={'S_token':.4,'Not_token':.6})
        self.assertTrue(validate_path_score(score))
        for changed in ('nan','wrongq','wrongmap','wrongbranch'):
            bad=deepcopy(score)
            if changed=='nan':bad['restricted_legal_q']['Supported']=float('nan')
            elif changed=='wrongq':bad['restricted_legal_q']=dict(zip(LABELS,[.6,.2,.2]))
            elif changed=='wrongmap':bad['restricted_legal_MAP']='Not Supported'
            else:bad['first_value_branch_raw_full_vocab_probabilities']['S_token']=1.2
            with self.assertRaises(ValueError):validate_path_score(bad)

    def test_completion_marker_requires_every_diagnostic_path(self):
        from run106 import verify_fixed_outputs
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'bundle';work=root/'work'
            c.put(bundle/'manifest.json',dict(task=106));sha=c.sha(bundle/'manifest.json')
            c.putl(bundle/'data/diagnostic_inputs.jsonl',[dict(id='fixed')])
            for prefix in ('eval','diagnostic'):c.put(bundle/'frozen'/(prefix+'_batches.json'),dict(batches=[dict(batch=0,ids=['fixed'])]))
            for arm in ('base_judge','label_mean','label_sum'):
                panels=('diagnostic','development') if arm=='label_sum' else ('diagnostic',)
                for panel in panels:c.put(work/'eval'/arm/panel/'batch-0000.json',dict(bundle_sha256=sha,ids=['fixed'],records=[dict(id='fixed',arm=arm)]))
                c.put(work/'eval'/arm/'diagnostic/complete_label_paths/fixed.json',dict(id='fixed',arm=arm,bundle_sha256=sha,complete_JSON_EOS_sum_logP={label:-1. for label in LABELS}))
            self.assertEqual(verify_fixed_outputs(bundle,work,'reuse')['complete_legal_paths'],9)
            (work/'eval/label_sum/diagnostic/complete_label_paths/fixed.json').unlink()
            with self.assertRaises(ValueError):verify_fixed_outputs(bundle,work,'reuse')

    def test_exact_tail_and_resume_cursor(self):
        sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
        from data105 import training_plan,validate_cursor
        plan=training_plan([str(i) for i in range(196)],2,8)
        self.assertEqual((len(plan),plan[-1]['consumed']),(50,392))
        for step in (0,1,25,49,50):
            consumed=plan[step-1]['consumed'] if step else 0
            self.assertEqual(len(validate_cursor(plan,step,consumed)),50-step)
        with self.assertRaises(ValueError):validate_cursor(plan,25,200)
        tails=[r['loss_divisor'] for r in plan if r['epoch_end']]
        self.assertEqual(tails,[4,4])

    def test_manifest_tamper_and_missing_new_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').write_text('fixed',encoding='utf-8')
            c.put(root/'manifest.json',dict(task=106,files={'data':c.sha(root/'data')}))
            verify_bundle(root)
            c.put(root/'authorization.json',dict(task=106,explicit_user_gpu_authorization=False))
            with self.assertRaises(PermissionError):verify_authorization(root,root/'authorization.json')
            (root/'data').write_text('changed',encoding='utf-8')
            with self.assertRaises(ValueError):verify_bundle(root)

    def test_manual_budget_guard_retains_billing_no_shutdown(self):
        import platform
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger=root/'compute106.json'
            state=dict(task=106,cap_cny=20,operating_line_cny=18,closed_sessions=[],
                       active=dict(machine=platform.node(),hourly_cny=8.,billing_start_epoch=1000.))
            self.assertAlmostEqual(used_cny(state,4600),8.)
            c.put(ledger,state)
            with patch('run106.time.time',return_value=10000.),patch('run106.subprocess.Popen',side_effect=AssertionError('No OS action')):
                watch(ledger)
                with self.assertRaises(TimeoutError):require_budget(ledger)
            self.assertTrue((root/'MANUAL_SHUTDOWN_REQUIRED.json').exists())
            self.assertFalse(c.read(root/'MANUAL_SHUTDOWN_REQUIRED.json').get('platform_shutdown_executed',False))
            self.assertIsNotNone(c.read(ledger)['active'])

    def test_worker_import_does_not_import_model_stack(self):
        importlib.import_module('worker106')
        self.assertNotIn('torch',sys.modules);self.assertNotIn('transformers',sys.modules)

    def test_raw_eval_truncation_no_fallback_and_hash_mismatch(self):
        from evaluate106 import collect,cover
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected={'fixed-id':{'prompt_token_sha256':'same-input'}}
            record=dict(id='fixed-id',arm='label_mean',prompt_token_sha256='same-input',content='{"verdict":"Supported"}',finish_reason='length')
            c.put(root/'batch-0000.json',dict(bundle_sha256='bundle-sha',ids=['fixed-id'],records=[record]))
            records=collect(root,expected,'bundle-sha','label_mean',{0:['fixed-id']})
            self.assertFalse(records['fixed-id']['parsed']['valid'])
            self.assertIsNone(records['fixed-id']['parsed']['verdict'])
            covered=cover([dict(id='fixed-id',GT='Not Supported')],records)
            self.assertEqual((covered['valid'],covered['invalid'],covered['missing']),(0,1,0))
            self.assertEqual(covered['PA_full_bounds'],[0.,1.])
            with self.assertRaises(ValueError):collect(root,{'fixed-id':{'prompt_token_sha256':'other-input'}},'bundle-sha','label_mean',{0:['fixed-id']})
            with self.assertRaises(ValueError):collect(root,expected,'bundle-sha','label_sum',{0:['fixed-id']})
            with self.assertRaises(ValueError):collect(root,expected,'bundle-sha','label_mean',{1:['fixed-id']})

    def test_training_diagnostic_patient_round_robin_fixed_only(self):
        from tokenizer106 import select_diagnostics
        rows=[dict(id=label+str(sid)+str(i),sid=str(sid),GT=label) for label in LABELS for sid in range(5) for i in range(2)]
        result=select_diagnostics(rows)
        self.assertEqual([r['id'] for r in result],[r['id'] for r in select_diagnostics(list(reversed(rows)))])
        for label in LABELS:
            chosen=[r for r in result if r['GT']==label]
            self.assertEqual(len(chosen),4);self.assertEqual(len({r['sid'] for r in chosen}),4)

    def test_frozen_gate_allows_small_risk_tradeoff_rejects_class_loss_and_missing(self):
        from copy import deepcopy
        from evaluate106 import development_decision
        def metrics(mcc,fs):return dict(mcc=mcc,percent_agreement=.80,false_S=fs,
            per_class={label:dict(recall=.6) for label in LABELS})
        panels={panel:dict(frozen_N=N,primary_training_arms_common_N=N,
            full_N_coverage={arm:dict(received=N,missing=0) for arm in ('label_mean','label_sum')},
            primary_metrics=dict(label_mean=metrics(.4,10),label_sum=metrics(.43,11),historical_label_only196=metrics(.4,10))) for panel,N in [('natural',400),('pressure',100)]}
        self.assertTrue(development_decision(panels)['worth_separately_authorized_confirmation_development'])
        too_risky=deepcopy(panels);too_risky['natural']['primary_metrics']['label_sum']['false_S']=12
        self.assertFalse(development_decision(too_risky)['worth_separately_authorized_confirmation_development'])
        risk_led=deepcopy(panels);risk_led['natural']['primary_metrics']['label_sum'].update(mcc=.391,false_S=6)
        self.assertTrue(development_decision(risk_led)['paths']['risk_led'])
        class_loss=deepcopy(panels);class_loss['pressure']['primary_metrics']['label_sum']['per_class']['Not Addressed']['recall']=.549
        self.assertFalse(development_decision(class_loss)['worth_separately_authorized_confirmation_development'])
        missing=deepcopy(panels);missing['pressure']['full_N_coverage']['label_sum']['missing']=1
        self.assertEqual(development_decision(missing)['status'],'execution_incomplete')

    def test_actual_confusion_matrices_block_shared_collapse(self):
        from evaluate106 import development_decision,metric
        # Valid GT/prediction tables, not hand-set MCC or self-referential gate
        # booleans. These verify arithmetic/guard logic, never clinical benefit.
        def measured(matrix):
            rows=[]
            for y,label in enumerate(LABELS):
                for j,pred in enumerate(LABELS):
                    for n in range(matrix[y][j]):rows.append(dict(id=str(len(rows)),sid=str(len(rows)%5),GT=label,pred={'test':pred}))
            return metric(rows,'test',profile='none')
        historical_n=[[284,29,8],[8,11,7],[9,16,28]]
        historical_p=[[0,0,0],[10,29,11],[8,9,33]]
        good_n=[[289,24,8],[7,14,5],[11,10,32]]
        good_p=[[0,0,0],[11,30,9],[8,7,35]]
        def panels(on,cn,op,cp):
            result={}
            for name,N,old,new,hist in [('natural',400,on,cn,historical_n),('pressure',100,op,cp,historical_p)]:
                result[name]=dict(frozen_N=N,primary_training_arms_common_N=N,
                    full_N_coverage={arm:dict(received=N,missing=0) for arm in ('label_mean','label_sum')},
                    primary_metrics=dict(label_mean=measured(old),label_sum=measured(new),historical_label_only196=measured(hist)))
            return result
        good=development_decision(panels(historical_n,good_n,historical_p,good_p))
        self.assertTrue(good['worth_separately_authorized_confirmation_development'])
        self.assertEqual(good['delta']['natural_false_S'],1)
        collapsed_n=[[0,0,321],[4,0,22],[0,0,53]];allna_n=[[0,0,321],[0,0,26],[0,0,53]]
        allna_p=[[0,0,0],[0,0,50],[0,0,50]];collapsed_p=allna_p
        allna=development_decision(panels(collapsed_n,allna_n,collapsed_p,allna_p))
        self.assertTrue(allna['paths']['risk_led'])
        self.assertTrue(all(allna['guards'].values()))
        self.assertFalse(allna['worth_separately_authorized_confirmation_development'])
        alls_n=[[321,0,0],[26,0,0],[53,0,0]];alls_p=[[0,0,0],[50,0,0],[50,0,0]]
        alls=development_decision(panels(historical_n,alls_n,historical_p,alls_p))
        self.assertFalse(alls['historical105_label196_usability_guards']['natural_Not Supported_nonzero_recall'])
        self.assertFalse(alls['historical105_label196_usability_guards']['natural_Not Addressed_nonzero_recall'])
        self.assertFalse(alls['worth_separately_authorized_confirmation_development'])

if __name__=='__main__':unittest.main(verbosity=2)
