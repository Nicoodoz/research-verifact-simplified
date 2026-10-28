"""Fixed label-sum target and bounded complete-label diagnostic scoring.

Torch is imported only by future authorized worker/tiny CPU tests. No model
weights, device initialization or network operation occurs at import.
"""
from __future__ import annotations
import math
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

def segmented_sum_loss(hidden,head,input_ids,groups,normalizer=360/196,chunk_tokens=16,checkpoint_head=True):
    if hidden.ndim!=3 or hidden.shape[0]!=1 or input_ids.shape!=groups.shape or hidden.shape[:2]!=groups.shape:raise ValueError('Frozen microbatch1 and aligned shapes required')
    if not ((groups==0)|(groups==1)|(groups==2)).all():raise ValueError('Unknown supervision group')
    if not math.isfinite(normalizer) or normalizer<=0 or chunk_tokens<1:raise ValueError('Positive fixed normalizer/chunk required')
    targets=input_ids[:,1:];kinds=groups[:,1:];selected=kinds>0
    states=hidden[:,:-1,:][selected];target=targets[selected];kind=kinds[selected]
    counts=[int((kind==k).sum().item()) for k in (1,2)]
    if not counts[0]:raise ValueError('Missing verdict supervision')
    weights=torch.where(kind==1,1/normalizer,1/max(counts[1],1)).to(torch.float32)
    def project_ce(h,y,w):return (F.cross_entropy(head(h).float(),y,reduction='none')*w).sum()
    total=hidden.new_zeros((),dtype=torch.float32)
    for start in range(0,len(target),chunk_tokens):
        args=(states[start:start+chunk_tokens],target[start:start+chunk_tokens],weights[start:start+chunk_tokens])
        total+=checkpoint(project_ce,*args,use_reentrant=False) if checkpoint_head and torch.is_grad_enabled() else project_ce(*args)
    return total,dict(verdict_tokens=counts[0],other_tokens=counts[1],projected_positions=len(target),max_head_rows=min(len(target),chunk_tokens),
                      value_sum_divisor=normalizer,value_per_token_weight=1/normalizer,other_total_weight=1 if counts[1] else 0)

def backbone_sum_loss(model,batch,normalizer=360/196,chunk_tokens=16):
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    if any(p.requires_grad for p in base.lm_head.parameters()):raise ValueError('LM head must remain frozen')
    outputs=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
    hidden=outputs.last_hidden_state if hasattr(outputs,'last_hidden_state') else outputs[0]
    return segmented_sum_loss(hidden,base.lm_head,batch['input_ids'],batch['groups'],normalizer,chunk_tokens)

def complete_path_scores(model,prompt_ids,label_sequences,first_value_index,branch_ids,device,chunk_tokens=16):
    """Three full canonical JSON+EOS paths, with distinct teacher-forced prefix.

    Returns sums, never token means. Stores no vocabulary logits. First-branch
    P(S-token)/P(Not-token) are raw full-vocabulary softmax at the same canonical
    JSON prefix, NOT three-class probabilities. Restricted q normalizes complete
    path likelihoods only and must not replace formal free-greedy verdicts.
    """
    base=model.get_base_model() if hasattr(model,'get_base_model') else model
    scores={};branch=None
    with torch.inference_mode():
        for label,answer_ids in label_sequences.items():
            ids=torch.tensor([prompt_ids+answer_ids],dtype=torch.long,device=device)
            out=base.model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,return_dict=True)
            hidden=out.last_hidden_state if hasattr(out,'last_hidden_state') else out[0]
            states=hidden[0,len(prompt_ids)-1:-1];targets=ids[0,len(prompt_ids):]
            if len(states)!=len(answer_ids):raise ValueError('Causal scoring span mismatch')
            logp=0.
            for start in range(0,len(targets),chunk_tokens):
                logits=base.lm_head(states[start:start+chunk_tokens]).float()
                selected=F.log_softmax(logits,dim=-1).gather(1,targets[start:start+chunk_tokens,None]).squeeze(1)
                logp+=float(selected.sum())
                if branch is None and start<=first_value_index<start+len(logits):
                    probabilities=F.softmax(logits[first_value_index-start],dim=-1)
                    branch={name:float(probabilities[index]) for name,index in branch_ids.items()}
                del logits,selected
            scores[label]=logp
            del ids,out,hidden,states,targets
    maximum=max(scores.values());weights={label:math.exp(score-maximum) for label,score in scores.items()};denom=sum(weights.values())
    q={label:value/denom for label,value in weights.items()}
    return dict(complete_JSON_EOS_sum_logP=scores,restricted_legal_q=q,restricted_legal_MAP=max(q,key=q.get),
                first_value_branch_raw_full_vocab_probabilities=branch,branch_is_not_three_class_probability=True,
                complete_paths_not_token_average=True,formal_greedy_not_replaced=True)
