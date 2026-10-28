"""Small CPU tensors/models only. No 9B weights, cloud or paid calls."""
import json
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
import common105 as c
from data105 import training_plan,validate_cursor
from loss105 import segmented_hidden_loss,backbone_loss
import checkpoint105 as ckpt
import budget105 as budget
from parse105 import parse

class Head(nn.Linear):
    def __init__(self,*args,**kw):super().__init__(*args,**kw);self.max_rows=0
    def forward(self,x):self.max_rows=max(self.max_rows,len(x));return super().forward(x)

class TinyBackbone(nn.Module):
    def __init__(self):
        super().__init__();self.emb=nn.Embedding(17,6);self.proj=nn.Linear(6,6);self.calls=0
    def forward(self,input_ids,**kw):
        self.calls+=1
        # Cumulative context is causal; this is not a large transformer.
        h=self.proj(self.emb(input_ids).cumsum(1)).tanh()
        return SimpleNamespace(last_hidden_state=h)

class TinyModel(nn.Module):
    def __init__(self):
        super().__init__();self.model=TinyBackbone();self.lm_head=Head(6,17,bias=False);self.lm_head.weight.requires_grad_(False)
    def save_pretrained(self,path,safe_serialization=True):torch.save(self.state_dict(),Path(path)/'toy_adapter.pt')

class CPUChecks(unittest.TestCase):
    def test_segmented_loss_gradient_shift_mask_and_empty_other(self):
        for groups in ([[0,0,2,1,1,2,0,0]],[[0,0,1,1,0,0,0,0]]):
            torch.manual_seed(17)
            h=torch.randn(1,8,5,dtype=torch.float64,requires_grad=True);head=Head(5,19,bias=False).double()
            ids=torch.randint(0,19,(1,8));g=torch.tensor(groups)
            actual,info=segmented_hidden_loss(h,head,ids,g,chunk_tokens=2)
            logits=head(h[:,:-1]);raw=F.cross_entropy(logits.reshape(-1,19),ids[:,1:].reshape(-1),reduction='none').view(1,-1)
            expected=sum(raw[g[:,1:]==k].mean() if (g[:,1:]==k).any() else raw.sum()*0 for k in (1,2))
            ga=torch.autograd.grad(actual,(h,head.weight),retain_graph=True);ge=torch.autograd.grad(expected,(h,head.weight))
            torch.testing.assert_close(actual.double(),expected,rtol=2e-6,atol=2e-6)
            for a,e in zip(ga,ge):torch.testing.assert_close(a,e,rtol=2e-6,atol=2e-6)
            self.assertEqual(info['projected_positions'],int((g>0).sum()))
            self.assertEqual(info['max_head_rows'],2)

    def test_single_backbone_and_bounded_head_with_actual_backward(self):
        torch.manual_seed(5);model=TinyModel();ids=torch.randint(0,17,(1,11));groups=torch.tensor([[0]*5+[2,2,1,2,2,0]])
        loss,info=backbone_loss(model,dict(input_ids=ids,attention_mask=torch.ones_like(ids),groups=groups),chunk_tokens=2)
        before=model.model.proj.weight.detach().clone();optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.01)
        loss.backward();optimizer.step()
        self.assertEqual(model.model.calls,1);self.assertLessEqual(model.lm_head.max_rows,2)
        self.assertFalse(torch.equal(before,model.model.proj.weight))
        self.assertEqual(info['verdict_tokens'],1)

    def test_two_epoch_tail_resume_rng_scheduler_and_final_save(self):
        plan=training_plan([str(i) for i in range(196)])
        self.assertEqual(len(plan),50);self.assertEqual([r['loss_divisor'] for r in plan if r['epoch_end']],[4,4])
        self.assertEqual([r['consumed'] for r in plan if r['epoch_end']],[196,392])
        with self.assertRaises(ValueError):validate_cursor(plan,25,200)
        def fresh():
            torch.manual_seed(9);np.random.seed(9);random.seed(9);m=TinyModel();o=torch.optim.AdamW(m.parameters(),lr=1e-4);s=torch.optim.lr_scheduler.LambdaLR(o,lambda _:1.)
            return m,o,s
        def advance(m,o,s,entries):
            for entry in entries:
                o.zero_grad(set_to_none=True)
                for item in entry['ids']:
                    x=torch.randn(1,6)*(.1+np.random.random()+random.random())
                    (m.model.proj(x).square().mean()/entry['loss_divisor']).backward()
                o.step();s.step()
        full,fo,fs=fresh();advance(full,fo,fs,plan)
        part,po,ps=fresh();advance(part,po,ps,plan[:25])
        with tempfile.TemporaryDirectory() as tmp:
            fp={'frozen':'toy'};ckpt.save(part,po,ps,tmp,25,196,fp)
            resumed,ro,rs=fresh()
            def restore(folder):resumed.load_state_dict(torch.load(folder/'toy_adapter.pt',weights_only=True))
            step,consumed,_=ckpt.load(ro,rs,tmp,fp,restore)
            advance(resumed,ro,rs,validate_cursor(plan,step,consumed))
            ckpt.save(resumed,ro,rs,tmp,50,392,fp)
            self.assertEqual(c.read(Path(tmp)/'resume.json')['consumed'],392)
            self.assertEqual(rs.last_epoch,50)
            for a,b in zip(full.parameters(),resumed.parameters()):torch.testing.assert_close(a,b,rtol=0,atol=0)
            final_step,final_consumed,_=ckpt.load(ro,rs,tmp,fp,restore)
            self.assertEqual(validate_cursor(plan,final_step,final_consumed),[])
            # A failed write to the inactive slot cannot replace the last pointer.
            pointer=(Path(tmp)/'resume.json').read_bytes()
            with patch.object(resumed,'save_pretrained',side_effect=RuntimeError('simulated save failure')):
                with self.assertRaises(RuntimeError):ckpt.save(resumed,ro,rs,tmp,50,392,fp)
            self.assertEqual((Path(tmp)/'resume.json').read_bytes(),pointer)

    def test_shared_parser_no_label_in_reason_or_truncated_fallback(self):
        self.assertEqual(parse('{"relation":"Supported is only quoted","verdict":"Not Supported"}')['verdict'],'Not Supported')
        self.assertFalse(parse('{"verdict":"Supported","verdict":"Not Supported"}')['valid'])
        self.assertFalse(parse('{"verdict":"Supported"}','length')['valid'])
        self.assertFalse(parse('{"relation":"Supported"}')['valid'])
        self.assertTrue(parse('Not Addressed')['exact_label_normalized'])

    def test_one_budget_across_nogpu_gpu_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';budget.initialize(path)
            with self.assertRaises(FileExistsError):budget.initialize(path)
            with patch.object(budget.time,'time',return_value=10000):
                budget.begin(path,'nogpu',1.,6400);budget.end(path,10000,True)
                budget.begin(path,'gpu',6.,10000)
            self.assertAlmostEqual(budget.total(c.read(path),now=13600),7.)
            with patch.object(budget.time,'time',return_value=20800):
                with self.assertRaises(TimeoutError):budget.require(path,120)
            with self.assertRaises(ValueError):budget.end(path,13600,False)
            self.assertEqual(c.read(path)['active']['kind'],'gpu')

    def test_promotion_keeps_risk_NS_PA_and_base_guard(self):
        from evaluate105 import gate
        def metrics(mcc,pa,fs,ns):return dict(mcc=mcc,percent_agreement=pa,false_S_rate=fs,per_class={'Not Supported':dict(recall=ns)})
        natural={'base_judge':metrics(.4,.8,.1,.5),'label_only':metrics(.45,.82,.12,.55),'evidence_brief':metrics(.48,.81,.12,.55)}
        pressure={'label_only':metrics(.3,.6,.2,.5),'evidence_brief':metrics(.3,.6,.2,.5)}
        self.assertTrue(gate(natural,pressure)['point_development_gate_pass'])
        pressure['evidence_brief']['false_S_rate']=.21
        self.assertFalse(gate(natural,pressure)['point_development_gate_pass'])
        pressure['evidence_brief']['false_S_rate']=.2
        natural['base_judge']=metrics(.5,.8,.1,.5)
        self.assertFalse(gate(natural,pressure)['conditions']['base_guard'])

if __name__=='__main__':unittest.main(verbosity=2)
