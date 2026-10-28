"""Meaningful CPU rejection/data/budget checks; no GPU, 9B or paid operations."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import math
from pathlib import Path
import platform
import sys
import tempfile
import time
import unittest
import common107 as c
from prepare107 import support_target, validate_training
from pack107 import validate_config
from run107 import verify_bundle, verify_authorization, used_cny, require_whole_remaining
from evaluate107 import collect, compare, cover, evaluate_run

class Checks(unittest.TestCase):
    def test_binary_mapping_and_unknown_rejected(self):
        self.assertEqual([support_target(y) for y in c.LABELS],[1,0,0])
        with self.assertRaises(ValueError):support_target('supported')

    def test_real_frozen_data_patient_and_GT_rejections(self):
        rows=c.rows(c.PRIVATE/'train/label_only.jsonl')
        roles=c.read(c.OUT/'patient_roles107.json')
        allowed=set(roles['train']);forbidden=set(roles['selection'])
        validate_training(rows,allowed,forbidden)
        altered=deepcopy(rows);altered[0]['sid']=next(iter(forbidden))
        with self.assertRaises(ValueError):validate_training(altered,allowed,forbidden)
        altered=deepcopy(rows);altered[0]['GT']='Not Addressed' if altered[0]['GT']!='Not Addressed' else 'Supported'
        with self.assertRaises(ValueError):validate_training(altered,allowed,forbidden)
        with self.assertRaises(ValueError):validate_training(rows[:-1],allowed,forbidden)

    def test_main_design_changes_rejected(self):
        config=c.read(c.TASK/'config.json');validate_config(config)
        for keys,value in [(('training','learning_rate'),2e-4),(('training','epochs'),3),
                           (('evaluation','batch_size'),8),(('training','loss'),'sum'),
                           (('budget','API_cap_cny'),1)]:
            changed=deepcopy(config);changed[keys[0]][keys[1]]=value
            with self.assertRaises(ValueError):validate_config(changed)
        changed=deepcopy(config);changed['training']['auxiliary']['weight']=2
        with self.assertRaises(ValueError):validate_config(changed)

    def test_package_tamper_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'bundle';root.mkdir();payload=root/'safe.json';c.put(payload,{'safe':True})
            manifest=root/'manifest.json';c.put(manifest,dict(task=107,files={'safe.json':c.sha(payload)}))
            verify_bundle(root)
            c.put(payload,{'safe':False})
            with self.assertRaises(ValueError):verify_bundle(root)
            outside=Path(folder)/'outside.json';c.put(outside,{})
            c.put(manifest,dict(task=107,files={'../outside.json':c.sha(outside)}))
            with self.assertRaises(ValueError):verify_bundle(root)

    def test_rental_and_price_bound_to_this_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);c.put(root/'manifest.json',dict(task=107,files={}))
            record=dict(task=107,user_supplied_rented_instance=True,user_request_reference='user107',
                hourly_cny=7.98,billing_start_epoch=time.time()-5,fixed_bundle_sha256=c.sha(root/'manifest.json'),cap_cny=20,API_cap_cny=0)
            c.put(root/'session.json',record);verify_authorization(root,root/'session.json')
            for key,value in [('user_supplied_rented_instance',False),('fixed_bundle_sha256','other'),('hourly_cny',0),('cap_cny',21),('API_cap_cny',1)]:
                bad=dict(record,**{key:value});c.put(root/'session.json',bad)
                with self.assertRaises((ValueError,PermissionError)):verify_authorization(root,root/'session.json')

    def test_complete_run_budget_rejects_before_optimization(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'compute107.json'
            state=dict(bundle_manifest_sha256='bundle107',operating_line_cny=18,cap_cny=20,API_cap_cny=0,
                active=dict(machine=platform.node(),hourly_cny=7.98,billing_start_epoch=time.time()-60),closed_sessions=[{'cost_cny':1}])
            c.put(ledger,state)
            gate=dict(status='PASS',bundle_sha256='bundle107',training_slowdown_vs105=1.,inference_slowdown_vs105=1.)
            estimate=dict(per_arm_train_remaining_seconds=1000,per_arm_eval_cautious_seconds=1000,remaining_overhead_seconds=300)
            result=require_whole_remaining(ledger,estimate,gate)
            self.assertTrue(result['fits_complete_frozen_run'])
            self.assertGreaterEqual(result['already_used_cny'],1.)
            estimate['per_arm_eval_cautious_seconds']=10000
            with self.assertRaises(TimeoutError):require_whole_remaining(ledger,estimate,gate)
            result=c.read(Path(folder)/'whole_run_budget_gate.json')
            self.assertFalse(result['formal_optimizer_updates_permitted'])
            self.assertGreater(result['remaining_budget_gap_cny'],0)
            with self.assertRaises(ValueError):require_whole_remaining(ledger,estimate,dict(gate,status='FAIL'))
            c.put(Path(folder)/'stop_requested.json',dict(reason='test'))
            with self.assertRaises(TimeoutError):require_whole_remaining(ledger,estimate,gate)

    def test_elapsed_cost_does_not_reset_prior_sessions(self):
        state=dict(closed_sessions=[dict(cost_cny=3)],adjustments_cny=.5,
                   active=dict(hourly_cny=8,billing_start_epoch=100))
        self.assertAlmostEqual(used_cny(state,3700),11.5)
        with self.assertRaises(ValueError):used_cny(state,99)

    def test_5090_absolute_budget_covers_every_frozen_small_batch(self):
        from cost107 import measured_remaining
        config=c.read(c.TASK/'config.json');batches=c.read(c.OUT/'eval_batches.json')['batches']
        maximum=max(b['max_input_tokens'] for b in batches)
        prefill=[dict(input_tokens=maximum,output_tokens_each=4,seconds=2.)]
        decode=[dict(output_tokens_each=128,seconds=8.),dict(output_tokens_each=384,seconds=20.)]
        estimate=measured_remaining(3273736,[dict(tokens=10000,seconds=5)],1.,.1,prefill,decode,batches,config)
        self.assertEqual(estimate['frozen_eval_batch_size'],2)
        self.assertEqual(estimate['frozen_eval_batch_count'],250)
        self.assertTrue(estimate['all500_may_generate384'])
        self.assertEqual(len(estimate['per_batch_estimates']),250)
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'compute107.json'
            c.put(ledger,dict(bundle_manifest_sha256='v2',operating_line_cny=18,cap_cny=20,
                active=dict(machine=platform.node(),hourly_cny=2.88,billing_start_epoch=time.time()-600)))
            gate=dict(status='PASS',bundle_sha256='v2',measured_run_estimate_seconds=estimate)
            receipt=require_whole_remaining(ledger,dict(runtime_estimate_mode='actual_gpu_absolute'),gate)
            self.assertTrue(receipt['fits_complete_frozen_run'])
            self.assertEqual(receipt['runtime_estimate_mode'],'actual_gpu_absolute')
            with self.assertRaises(ValueError):require_whole_remaining(ledger,dict(runtime_estimate_mode='actual_gpu_absolute'),dict(gate,measured_run_estimate_seconds={}))

    def test_first_invalid_is_retained_and_wrong_arm_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            row=dict(id='synthetic_only',arm='support_aux',prompt_token_sha256='same',
                     content='not JSON',finish_reason='stop',output_tokens=2)
            batch=dict(ids=[row['id']],bundle_sha256='frozen',batch_seconds=1,aux_head_used=False,records=[row])
            c.put(root/'batch-0000.json',batch)
            records,cost=collect(root,{row['id']:{'prompt_token_sha256':'same'}},'frozen','support_aux',{0:[row['id']]})
            self.assertFalse(records[row['id']]['parsed']['valid'])
            coverage=cover([dict(id=row['id'],sid='p',GT='Not Supported')],records)
            self.assertEqual((coverage['received'],coverage['valid'],coverage['invalid']),(1,0,1))
            self.assertEqual(coverage['false_S_full_bounds'],[0.,1.])
            with self.assertRaises(ValueError):collect(root,{row['id']:{'prompt_token_sha256':'same'}},'frozen','label_only',{0:[row['id']]})
            batch['aux_head_used']=True;c.put(root/'batch-0000.json',batch)
            with self.assertRaises(ValueError):collect(root,{row['id']:{'prompt_token_sha256':'same'}},'frozen','support_aux',{0:[row['id']]})

    def test_fewer_S_has_visible_S_harm_and_nonS_risk_transfer(self):
        S,NS,NA=c.LABELS
        specs=[('p1',S,S,NS),('p2',S,NA,S),('p1',NS,S,NS),('p2',NA,NS,S),('p2',NA,NA,NS),('p1',NS,NS,NS)]
        rows=[dict(id='synthetic_'+str(i),sid=p,GT=gt,pred=dict(label_only=b,support_aux=a)) for i,(p,gt,b,a) in enumerate(specs)]
        result=compare(rows)
        self.assertEqual((result['by_true_class'][S]['rescued'],result['by_true_class'][S]['harmed']),(1,1))
        self.assertEqual((result['by_true_class'][NA]['rescued'],result['by_true_class'][NA]['harmed']),(0,1))
        self.assertEqual((result['false_S_new'],result['false_S_avoided']),(1,1))
        self.assertEqual(result['primary']['metrics']['percent_agreement']['delta'],0.)
        self.assertEqual(result['predicted_S'],dict(label_only=2,support_aux=2))

    def test_two_new_arm_common_IDs_and_empty_panel_report(self):
        # Synthetic receipt fixture only, never a 9B score or actual run output.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);bundle=root/'bundle';results=root/'results'
            keys=[]
            for panel,labels in [('natural',c.LABELS*2),('pressure',c.LABELS[1:]*2)]:
                for i,label in enumerate(labels):
                    keys.append(dict(id=panel+str(i),sid='p'+str(i%2),panel=panel,GT=label,paper_r1=label,author='human'))
            c.putl(bundle/'frozen/eval_keys.jsonl',keys)
            c.putl(bundle/'frozen/eval_token_lengths.jsonl',[dict(id=r['id'],prompt_token_sha256='token_'+r['id']) for r in keys])
            c.put(bundle/'frozen/eval_batches.json',dict(batches=[dict(batch=0,ids=[r['id'] for r in keys])]))
            c.put(bundle/'manifest.json',dict(task=107,files={p.relative_to(bundle).as_posix():c.sha(p) for p in (bundle/'frozen').iterdir()}))
            for arm in c.ARMS:
                records=[]
                for row in keys:
                    invalid=arm=='support_aux' and (row['id']=='natural0' or row['panel']=='pressure')
                    records.append(dict(id=row['id'],arm=arm,prompt_token_sha256='token_'+row['id'],
                        content='invalid' if invalid else c.canonical({'verdict':row['GT']}),finish_reason='stop',output_tokens=3))
                c.put(results/'eval'/arm/'development/batch-0000.json',dict(ids=[r['id'] for r in keys],
                    bundle_sha256=c.sha(bundle/'manifest.json'),batch_seconds=1,aux_head_used=False,records=records))
            with redirect_stdout(io.StringIO()):report=evaluate_run(bundle,results,root/'synthetic_analysis.json')
            self.assertEqual(report['panels']['natural']['common_valid_N'],5)
            self.assertNotIn('natural0',report['panels']['natural']['common_ids'])
            self.assertEqual(report['panels']['pressure']['common_valid_N'],0)
            self.assertIsNone(report['panels']['pressure']['metrics']['support_aux'])
            self.assertTrue(report['panels']['pressure']['paired']['evidence_insufficient'])
            self.assertTrue(report['all_frozen_first_requests_received'])
            self.assertTrue(report['evidence_insufficient'])
            self.assertEqual(report['panels']['pressure']['full_N_coverage']['support_aux']['invalid'],4)

def main():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    c.put(c.OUT/'cpu_checks.json',dict(task=107,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        passed=result.wasSuccessful(),environment='research-verifact-029',
        torch_imported='torch' in sys.modules,transformers_imported='transformers' in sys.modules,
        GPU_calls=0,API_calls=0,target_model_loaded=False,clinical_text_in_report=False,
        limitation='Implementation/data/budget rejection tests only; not method effectiveness or real9B readiness'))
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
