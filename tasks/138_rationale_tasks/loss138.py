"""Bounded all-answer CE for an auxiliary text task; label CE stays loss105."""
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint
def answer_hidden_loss(hidden,head,input_ids,groups,chunk_tokens=16):
 selected=groups[:,1:]>0
 if not selected.any():raise ValueError('No auxiliary answer tokens')
 states=hidden[:,:-1,:][selected];targets=input_ids[:,1:][selected]
 total=hidden.new_zeros((),dtype=torch.float32)
 def ce(h,y):return F.cross_entropy(head(h).float(),y,reduction='sum')/len(targets)
 for start in range(0,len(targets),chunk_tokens):
  args=(states[start:start+chunk_tokens],targets[start:start+chunk_tokens])
  total=total+(checkpoint(ce,*args,use_reentrant=False) if torch.is_grad_enabled() else ce(*args))
 return total,dict(answer_tokens=len(targets),max_head_rows=min(chunk_tokens,len(targets)))
def reason_backbone_loss(model,batch,chunk_tokens=16):
 base=model.get_base_model() if hasattr(model,'get_base_model') else model
 if any(p.requires_grad for p in base.lm_head.parameters()):raise ValueError('Frozen LM head required')
 result=base.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False,return_dict=True)
 hidden=result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]
 return answer_hidden_loss(hidden,base.lm_head,batch['input_ids'],batch['groups'],chunk_tokens)
