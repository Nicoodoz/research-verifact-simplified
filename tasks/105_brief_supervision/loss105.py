"""One backbone forward; project only answer states in bounded CE chunks.

Only states predicting answer targets reach the LM head (including the last
prompt state predicting the first answer token). No prompt/padding targets have
loss. Non-reentrant checkpointing recomputes
only each small projection/CE chunk in backward, never a second backbone pass.
No [sequence,vocab] FP32 tensor is created. The LM head remains frozen.
"""
from __future__ import annotations
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

def segmented_hidden_loss(hidden,head,input_ids,groups,chunk_tokens=16,checkpoint_head=True):
    if hidden.ndim!=3 or input_ids.shape!=groups.shape or hidden.shape[:2]!=groups.shape:raise ValueError('Shape mismatch')
    if not ((groups==0)|(groups==1)|(groups==2)).all():raise ValueError('Unknown supervision group')
    if chunk_tokens<1:raise ValueError('Positive bounded head chunk required')
    # A state at t predicts the target at t+1. Group 0 is prompt/padding.
    targets=input_ids[:,1:];kinds=groups[:,1:]
    selected=kinds>0
    if not selected.any():raise ValueError('No supervised answer positions')
    states=hidden[:,:-1,:][selected];target=targets[selected];kind=kinds[selected]
    counts=[int((kind==k).sum().item()) for k in (1,2)]
    if counts[0]==0:raise ValueError('A classification value is required')
    weights=torch.where(kind==1,1./counts[0],1./max(counts[1],1)).to(torch.float32)
    total=hidden.new_zeros((),dtype=torch.float32)
    # The closure never captures changing loop variables or token labels.
    def project_ce(h,y,w):
        logits=head(h)
        return (F.cross_entropy(logits.float(),y,reduction='none')*w).sum()
    for start in range(0,len(target),chunk_tokens):
        args=(states[start:start+chunk_tokens],target[start:start+chunk_tokens],weights[start:start+chunk_tokens])
        total=total+(checkpoint(project_ce,*args,use_reentrant=False) if checkpoint_head and torch.is_grad_enabled() else project_ce(*args))
    return total,dict(verdict_tokens=counts[0],other_tokens=counts[1],projected_positions=len(target),max_head_rows=min(len(target),chunk_tokens))

def backbone_loss(model,batch,chunk_tokens=16):
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    if not hasattr(base,'model') or not hasattr(base,'lm_head'):raise TypeError('Expected pinned Qwen3.5 conditional-generation backbone/head')
    if any(p.requires_grad for p in base.lm_head.parameters()):raise ValueError('LM head must remain frozen')
    outputs=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
    hidden=outputs.last_hidden_state if hasattr(outputs,'last_hidden_state') else outputs[0]
    return segmented_hidden_loss(hidden,base.lm_head,batch['input_ids'],batch['groups'],chunk_tokens)

