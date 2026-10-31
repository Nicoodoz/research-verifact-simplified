"""Unchanged105 CE plus0.5 forward KL at causal label targets only.

The backbone runs once. State at index t predicts input_ids[t+1]; group1
marks label targets, group2 other answer targets, group0 prompt/padding.
Teacher states retain their original dtype and are never trained. Softmax and
KL accumulation are FP32 over the full vocabulary, averaged within each
example and then across examples. No sequence-by-vocabulary tensor is built.
"""
from pathlib import Path
import hashlib
import sys
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'105_brief_supervision'))
from loss105 import segmented_hidden_loss as ce105


def label_indices(groups):
    if groups.ndim!=2 or groups.shape[1]<2:raise ValueError('Expected batch x sequence groups')
    if not ((groups==0)|(groups==1)|(groups==2)).all():raise ValueError('Unknown supervision group')
    indices=[torch.nonzero(row[1:]==1,as_tuple=False).flatten() for row in groups]
    if any(len(i)==0 for i in indices):raise ValueError('Every example requires label targets')
    return indices


def sampled_head_fingerprint(head,max_elements=2048):
    """Sampled identity only: shape/dtype and fixed evenly spaced scalar values.

    This is deliberately not a full checksum of the roughly2GB frozen head.
    The pinned base config and source120 adapter identity remain separate.
    """
    if any(p.requires_grad for p in head.parameters()):raise ValueError('LM head must be frozen')
    h=hashlib.sha256()
    with torch.no_grad():
        for name,tensor in sorted(head.state_dict().items()):
            h.update(f'{name}|{tensor.dtype}|{tuple(tensor.shape)}'.encode())
            flat=tensor.detach().reshape(-1);count=min(flat.numel(),max_elements)
            indices=torch.div(torch.arange(count,device=flat.device)*max(flat.numel()-1,0),max(count-1,1),rounding_mode='floor')
            part=flat[indices].contiguous().view(torch.uint8).cpu()
            h.update(part.numpy().tobytes())
    return h.hexdigest()


def anchored_hidden_loss(hidden,head,input_ids,groups,teacher_hidden,chunk_tokens=16,
                         lambda_kl=0.5,temperature=1.0,checkpoint_head=True):
    if lambda_kl!=0.5 or temperature!=1.0:raise ValueError('Frozen140 requires lambda0.5 and T1')
    if any(p.requires_grad for p in head.parameters()):raise ValueError('LM head must be frozen')
    if hidden.ndim!=3 or hidden.shape[:2]!=input_ids.shape or groups.shape!=input_ids.shape:
        raise ValueError('Shape mismatch')
    if chunk_tokens<1:raise ValueError('Positive bounded head chunk required')
    indices=label_indices(groups)
    if isinstance(teacher_hidden,torch.Tensor):
        if hidden.shape[0]!=1:raise ValueError('Multi-example teacher states must be a list')
        teacher_hidden=[teacher_hidden]
    if len(teacher_hidden)!=hidden.shape[0]:raise ValueError('Teacher batch count differs')
    ces=[];kls=[];counts=[]
    def forward_kl(student,teacher):
        #The same frozen head maps both representations to the vocabulary.
        log_student=F.log_softmax(head(student).float(),dim=-1)
        with torch.no_grad():log_teacher=F.log_softmax(head(teacher).float(),dim=-1)
        return (log_teacher.exp()*(log_teacher-log_student)).sum(dim=-1).sum()
    for b,index in enumerate(indices):
        target=teacher_hidden[b]
        if target.requires_grad:raise ValueError('Teacher cache must be detached')
        if target.ndim!=2 or target.shape!=(len(index),hidden.shape[-1]):raise ValueError('Teacher label layout differs')
        if target.dtype!=hidden.dtype:raise ValueError('Teacher dtype changed; no implicit cache quantization')
        teacher=target.to(device=hidden.device)
        student=hidden[b,index,:]
        ce,info=ce105(hidden[b:b+1],head,input_ids[b:b+1],groups[b:b+1],chunk_tokens,checkpoint_head)
        divergence=hidden.new_zeros((),dtype=torch.float32)
        for start in range(0,len(index),chunk_tokens):
            args=(student[start:start+chunk_tokens],teacher[start:start+chunk_tokens])
            divergence=divergence+(checkpoint(forward_kl,*args,use_reentrant=False)
                if checkpoint_head and torch.is_grad_enabled() else forward_kl(*args))
        ces.append(ce);kls.append(divergence/len(index));counts.append(info)
    ce=torch.stack(ces).mean();kl=torch.stack(kls).mean();total=ce+lambda_kl*kl
    return total,dict(ce=ce.detach(),kl=kl.detach(),label_positions=[len(i) for i in indices],
        original_CE=counts,teacher_detached=True,temperature=temperature,lambda_kl=lambda_kl)


def backbone_loss(model,batch,teacher_hidden,chunk_tokens=16,lambda_kl=0.5,temperature=1.0):
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    if not hasattr(base,'model') or not hasattr(base,'lm_head'):raise TypeError('Expected pinned Qwen backbone/head')
    if any(p.requires_grad for p in base.lm_head.parameters()):raise ValueError('Frozen LM head required')
    result=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
    hidden=result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]
    return anchored_hidden_loss(hidden,base.lm_head,batch['input_ids'],batch['groups'],teacher_hidden,
                                chunk_tokens,lambda_kl,temperature)


@torch.no_grad()
def teacher_states(model,batch):
    """One source120 backbone forward, copied to CPU without dtype conversion."""
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    if any(p.requires_grad for p in base.lm_head.parameters()):raise ValueError('Frozen LM head required')
    result=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
    hidden=result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]
    indices=label_indices(batch['groups'])
    return [hidden[b,index,:].detach().cpu().contiguous().clone() for b,index in enumerate(indices)]
