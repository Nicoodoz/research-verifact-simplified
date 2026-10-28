"""Existing 032 environment, tiny CPU tensors only; selected 105 proven paths."""
import sys
from pathlib import Path
import unittest
import random
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'105_brief_supervision'))
from test_cpu105 import CPUChecks,TinyModel
from data105 import training_plan,validate_cursor
import checkpoint105 as ckpt
from loss106 import segmented_sum_loss,backbone_sum_loss,complete_path_scores

class NewScheduleChecks(unittest.TestCase):
    def test_196_sum_twice_resume_matches_uninterrupted(self):
        plan=training_plan([str(i) for i in range(196)],2,8)
        def fresh():
            torch.manual_seed(106);np.random.seed(106);random.seed(106)
            model=TinyModel();optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4)
            scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda _:1.)
            return model,optimizer,scheduler
        def advance(model,optimizer,scheduler,entries):
            for entry in entries:
                optimizer.zero_grad(set_to_none=True)
                for identifier in entry['ids']:
                    n=1+int(identifier)%3;ids=torch.randint(0,17,(1,10));groups=torch.tensor([[0]*(8-n)+[1]*n+[2,2]])
                    # RNG-dependent tiny causal computation, actual selected
                    # sum loss and four-row tail; no clinical/model efficacy.
                    scale=.1+random.random()+np.random.random()
                    loss,_=backbone_sum_loss(model,dict(input_ids=ids,attention_mask=torch.ones_like(ids),groups=groups),360/196,2)
                    (loss*scale/entry['loss_divisor']).backward()
                optimizer.step();scheduler.step()
        full,fo,fs=fresh();advance(full,fo,fs,plan)
        partial,po,ps=fresh();advance(partial,po,ps,plan[:25])
        with tempfile.TemporaryDirectory() as tmp:
            fp={'task106':'tiny196_sum_no_clinical_effect'}
            ckpt.save(partial,po,ps,tmp,25,196,fp)
            resumed,ro,rs=fresh()
            def restore(folder):resumed.load_state_dict(torch.load(Path(folder)/'toy_adapter.pt',weights_only=True))
            step,consumed,_=ckpt.load(ro,rs,tmp,fp,restore)
            advance(resumed,ro,rs,validate_cursor(plan,step,consumed))
            self.assertEqual(rs.last_epoch,50)
            for left,right in zip(full.parameters(),resumed.parameters()):torch.testing.assert_close(left,right,atol=0,rtol=0)
        self.assertFalse(torch.cuda.is_initialized())

    def test_sum_loss_value_gradient_global_constant(self):
        for n in (1,2,3):
            torch.manual_seed(106)
            h=torch.randn(1,12,6,dtype=torch.float64,requires_grad=True);head=torch.nn.Linear(6,17,bias=False).double()
            ids=torch.randint(0,17,(1,12));groups=torch.tensor([[0]*(6-n)+[1]*n+[2]*6])
            loss,info=segmented_sum_loss(h,head,ids,groups,360/196,2)
            raw=torch.nn.functional.cross_entropy(head(h[:,:-1]).reshape(-1,17),ids[:,1:].reshape(-1),reduction='none').view(1,-1)
            expected=raw[groups[:,1:]==1].sum()/(360/196)+raw[groups[:,1:]==2].mean()
            got=torch.autograd.grad(loss,(h,head.weight),retain_graph=True);want=torch.autograd.grad(expected,(h,head.weight))
            torch.testing.assert_close(loss.double(),expected,atol=2e-6,rtol=2e-6)
            for a,b in zip(got,want):torch.testing.assert_close(a,b,atol=2e-6,rtol=2e-6)
            self.assertEqual(info['verdict_tokens'],n);self.assertAlmostEqual(info['value_per_token_weight'],196/360)
        self.assertAlmostEqual((83+62*2+51*3)/(360/196)/196,1.)

    def test_complete_paths_and_raw_branch_match_full_tiny_reference(self):
        torch.manual_seed(106);model=TinyModel();model.eval();prompt=[2,3,4]
        sequences={'Supported':[5,6,7],'Not Supported':[5,8,9,7],'Not Addressed':[5,8,10,11,7]}
        result=complete_path_scores(model,prompt,sequences,1,{'S_token':6,'Not_token':8},'cpu',2)
        expected={};branch=None
        with torch.inference_mode():
            for label,answer in sequences.items():
                ids=torch.tensor([prompt+answer]);hidden=model.model(input_ids=ids).last_hidden_state
                logits=model.lm_head(hidden[0,len(prompt)-1:-1]).float()
                expected[label]=float(torch.log_softmax(logits,-1).gather(1,torch.tensor(answer)[:,None]).sum())
                if branch is None:
                    p=torch.softmax(logits[1],-1);branch={'S_token':float(p[6]),'Not_token':float(p[8])}
        for label,value in expected.items():self.assertAlmostEqual(value,result['complete_JSON_EOS_sum_logP'][label],places=5)
        for key,value in branch.items():self.assertAlmostEqual(value,result['first_value_branch_raw_full_vocab_probabilities'][key],places=7)
        self.assertAlmostEqual(sum(result['restricted_legal_q'].values()),1.)
        self.assertTrue(result['formal_greedy_not_replaced'])

    def test_resume_missing_path_scores_never_regenerates_saved_greedy(self):
        import common106 as c
        import worker106
        class Tokenizer:
            pad_token_id=0;eos_token_id=3
            def apply_chat_template(self,*args,**kwargs):return [1,2]
            def convert_tokens_to_ids(self,token):return 3
            def encode(self,text,add_special_tokens=False):return [1,2]
        class NoGenerate:
            def eval(self):return self
            def generate(self,**kwargs):raise AssertionError('Already saved greedy answer must not be regenerated')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'bundle';work=root/'results'
            c.put(bundle/'manifest.json',{'task':106})
            sha=c.sha(bundle/'manifest.json');prompt_sha=c.digest(c.canonical([1,2]))
            c.putl(bundle/'data/diagnostic_inputs.jsonl',[dict(id='fixed',sid='train',claim='synthetic statement',reference='synthetic reference',panel='train_diagnostic')])
            c.putl(bundle/'frozen/diagnostic_token_lengths.jsonl',[dict(id='fixed',prompt_token_sha256=prompt_sha)])
            c.put(bundle/'frozen/diagnostic_batches.json',dict(batches=[dict(batch=0,ids=['fixed'])]))
            c.put(bundle/'frozen/tokenizer_labels.json',dict(labels={'Supported':dict(verdict_ids=[6],verdict_indices=[1]),'Not Supported':dict(verdict_ids=[8])}))
            raw_path=work/'eval/base_judge/diagnostic/batch-0000.json'
            c.put(raw_path,dict(ids=['fixed'],bundle_sha256=sha,records=[dict(id='fixed',arm='base_judge',content='Supported',finish_reason='stop')]))
            before=raw_path.read_bytes()
            a=SimpleNamespace(bundle=bundle,work=work,arm='base_judge',panel='diagnostic',ledger=root/'ledger.json')
            fake_score=dict(complete_JSON_EOS_sum_logP={l:-1. for l in c.LABELS},restricted_legal_q={l:1/3 for l in c.LABELS},restricted_legal_MAP='Supported',
                            first_value_branch_raw_full_vocab_probabilities={'S_token':.4,'Not_token':.5},formal_greedy_not_replaced=True)
            with patch.object(worker106,'require_budget',return_value=None),patch('loss106.complete_path_scores',return_value=fake_score) as score:
                worker106.evaluate(a,{'training':{'head_chunk_tokens':16}},NoGenerate(),Tokenizer(),SimpleNamespace(for_inference=lambda model:None),None)
                self.assertEqual(score.call_count,1)
                worker106.evaluate(a,{'training':{'head_chunk_tokens':16}},NoGenerate(),Tokenizer(),SimpleNamespace(for_inference=lambda model:None),None)
                self.assertEqual(score.call_count,1)
            self.assertEqual(raw_path.read_bytes(),before)

if __name__=='__main__':
    suite=unittest.TestSuite(CPUChecks(name) for name in (
        'test_segmented_loss_gradient_shift_mask_and_empty_other',
        'test_single_backbone_and_bounded_head_with_actual_backward',
        'test_two_epoch_tail_resume_rng_scheduler_and_final_save'))
    for name in ('test_196_sum_twice_resume_matches_uninterrupted','test_sum_loss_value_gradient_global_constant','test_complete_paths_and_raw_branch_match_full_tiny_reference','test_resume_missing_path_scores_never_regenerates_saved_greedy'):suite.addTest(NewScheduleChecks(name))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if torch.cuda.is_initialized():raise RuntimeError('Tiny CPU tests unexpectedly initialized CUDA')
    raise SystemExit(0 if result.wasSuccessful() else 1)
