"""Small deterministic CPU fixtures; no clinical predictions or GPU activity."""
from pathlib import Path
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
import ast,json,sys
import torch
from torch import nn
from torch.nn import functional as F
from types import SimpleNamespace
from loss140 import anchored_hidden_loss,backbone_loss,teacher_states,label_indices,sampled_head_fingerprint,ce105
from worker140 import validate_cache_identity,unique_training_rows
R=Path(__file__).resolve().parents[2]


def expect_error(call):
    try:call()
    except (ValueError,RuntimeError):return
    raise AssertionError('Required guard did not reject invalid input')


def main():
    torch.manual_seed(140)
    head=nn.Linear(4,7,bias=False);head.requires_grad_(False)
    ids=torch.tensor([[0,1,2,3,4,5],[6,5,4,0,0,0]])
    groups=torch.tensor([[0,0,1,1,2,2],[0,1,2,0,0,0]])
    indices=label_indices(groups)
    assert [v.tolist() for v in indices]==[[1,2],[0]]
    hidden=torch.randn(2,6,4,requires_grad=True)
    teacher=[torch.randn(2,4),torch.randn(1,4)]
    loss,info=anchored_hidden_loss(hidden,head,ids,groups,teacher,chunk_tokens=1)
    reference_ce=sum(ce105(hidden[b:b+1],head,ids[b:b+1],groups[b:b+1],checkpoint_head=False)[0] for b in range(2))/2
    reference_kl=hidden.new_zeros(())
    for b,index in enumerate(indices):
        lp=F.log_softmax(head(hidden[b,index]).float(),dim=-1)
        lq=F.log_softmax(head(teacher[b]).float(),dim=-1)
        reference_kl+=((lq.exp()*(lq-lp)).sum(-1)).mean()/2
    reference=reference_ce+.5*reference_kl
    assert torch.allclose(loss,reference,atol=1e-6,rtol=1e-6)
    grad=torch.autograd.grad(loss,hidden,retain_graph=True)[0]
    grad_ref=torch.autograd.grad(reference,hidden,retain_graph=True)[0]
    assert torch.allclose(grad,grad_ref,atol=2e-6,rtol=2e-6)
    grad_ce=torch.autograd.grad(reference_ce,hidden,retain_graph=True)[0]
    for b in range(2):
        for t in range(6):
            if t not in indices[b].tolist():assert torch.allclose(grad[b,t],grad_ce[b,t],atol=1e-7)
    assert torch.count_nonzero(grad[:,5,:])==0
    assert info['label_positions']==[2,1] and all(t.grad is None for t in teacher)
    equal_teacher=[hidden[b,index].detach().clone() for b,index in enumerate(indices)]
    equal_loss,equal_info=anchored_hidden_loss(hidden,head,ids,groups,equal_teacher,checkpoint_head=False)
    equal_grad=torch.autograd.grad(equal_loss,hidden,retain_graph=True)[0]
    assert abs(float(equal_info['kl']))<1e-7 and torch.allclose(equal_grad,grad_ce,atol=2e-7)
    expect_error(lambda:anchored_hidden_loss(hidden,head,ids,groups,[teacher[0][:1],teacher[1]]))
    expect_error(lambda:anchored_hidden_loss(hidden,head,ids,groups,[teacher[0].requires_grad_(),teacher[1]]))
    teacher[0]=teacher[0].detach()
    expect_error(lambda:anchored_hidden_loss(hidden,head,ids,groups,[t.double() for t in teacher]))
    head.requires_grad_(True);expect_error(lambda:anchored_hidden_loss(hidden,head,ids,groups,teacher));head.requires_grad_(False)
    before=sampled_head_fingerprint(head)
    assert before==sampled_head_fingerprint(head)
    with torch.no_grad():head.weight[0,0]+=1
    assert before!=sampled_head_fingerprint(head)
    class Backbone(nn.Module):
        def __init__(self):super().__init__();self.embedding=nn.Embedding(7,4);self.calls=0
        def forward(self,input_ids,**kwargs):
            self.calls+=1;return SimpleNamespace(last_hidden_state=self.embedding(input_ids))
    class Model(nn.Module):
        def __init__(self):super().__init__();self.model=Backbone();self.lm_head=head
    model=Model();batch=dict(input_ids=ids[:1],attention_mask=torch.ones_like(ids[:1]),groups=groups[:1])
    cached=teacher_states(model,batch)
    assert model.model.calls==1 and cached[0].dtype==torch.float32 and not cached[0].requires_grad
    model.model.calls=0
    one_loss,_=backbone_loss(model,batch,cached[0]);one_loss.backward()
    assert model.model.calls==1 and all(p.grad is None for p in head.parameters())
    expect_error(lambda:validate_cache_identity(None,{'source':'120'},True))
    expect_error(lambda:validate_cache_identity({'identity':{'source':'student'},'complete':True},{'source':'120'},True))
    expect_error(lambda:validate_cache_identity({'identity':{'source':'120'},'complete':False},{'source':'120'},True))
    validate_cache_identity({'identity':{'source':'120'},'complete':True},{'source':'120'},True)
    fixture=dict(original_id='id-one',sample_id='label/id-one',kind='label',input_ids=[1,2],groups=[0,1])
    duplicate=dict(fixture,sample_id='aux/id-one')
    assert len(unique_training_rows([fixture,duplicate]))==1
    expect_error(lambda:unique_training_rows([fixture,dict(duplicate,input_ids=[1,3])]))
    for path in (R/'tasks/140_kl_anchor').glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    assert not torch.cuda.is_initialized()
    result=dict(status='PASS',device='CPU',loss_value=float(loss.detach()),reference_value=float(reference.detach()),
        loss_absolute_error=float(abs(loss-reference).detach()),max_gradient_error=float((grad-grad_ref).abs().max()),
        initial_KL=float(equal_info['kl']),causal_shift=True,per_example_mean=True,
        KL_only_on_group1=True,full_vocabulary_FP32=True,teacher_no_gradient=True,head_frozen=True,
        teacher_dtype_preserved=True,one_student_backbone_forward=True,
        sampled_head_fingerprint_checked=True,head_full_checksum_performed=False,
        resume_missing_or_wrong_teacher_rejected=True,duplicate_ID_consistency=True,
        GPU_used=False,clinical_predictions_generated=False)
    out=R/'.local_models/140_kl_anchor/cpu_checks.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'));print(json.dumps(result))


if __name__=='__main__':main()
