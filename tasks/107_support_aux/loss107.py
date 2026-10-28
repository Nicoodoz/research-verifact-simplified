"""105 main loss plus a training-only prompt-last S/non-S readout.

The exact 105 segmented CE implementation is imported, not reimplemented.
Both losses consume a single causal backbone forward.  The binary readout
uses the state immediately BEFORE the first answer token.  Its parameters are
separate from the inference adapter; no auxiliary output is used at inference.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '105_brief_supervision'))
from loss105 import segmented_hidden_loss


class SupportHead(nn.Module):
    """FP32 linear binary head, initialized without advancing any global RNG."""

    def __init__(self, hidden_size, seed=103028):
        super().__init__()
        if type(hidden_size) is not int or hidden_size < 1:
            raise ValueError('Positive hidden size required')
        generator = torch.Generator(device='cpu').manual_seed(seed)
        self.weight = nn.Parameter(torch.empty((1, hidden_size), dtype=torch.float32))
        self.bias = nn.Parameter(torch.empty((1,), dtype=torch.float32))
        # These are the standard nn.Linear reset_parameters distributions.
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5), generator=generator)
        nn.init.uniform_(self.bias, -1 / math.sqrt(hidden_size), 1 / math.sqrt(hidden_size), generator=generator)

    def forward(self, hidden):
        # Explicitly leave the worker's BF16 autocast region: .float() alone
        # would still allow autocast to downcast the linear operation.
        with torch.autocast(device_type=hidden.device.type, enabled=False):
            return F.linear(hidden.float(), self.weight, self.bias)


def make_aux_head(hidden_size, seed=103028, device=None):
    head = SupportHead(hidden_size, seed)
    return head.to(device=device) if device is not None else head


def prompt_states(hidden, batch):
    """Read prompt-last only; reject answer/padding or an ambiguous boundary."""
    if hidden.ndim != 3 or hidden.shape[:2] != batch['input_ids'].shape:
        raise ValueError('Hidden/input shape mismatch')
    lengths = torch.as_tensor(batch['prompt_tokens'], device=hidden.device)
    if lengths.ndim == 0:
        lengths = lengths.unsqueeze(0)
    if lengths.shape != (hidden.shape[0],) or lengths.dtype == torch.bool or lengths.is_floating_point():
        raise ValueError('One integer prompt boundary is required per row')
    if bool(((lengths < 1) | (lengths >= hidden.shape[1])).any()):
        raise ValueError('Prompt must be nonempty and precede the answer')
    groups = batch['groups']
    attention = batch['attention_mask']
    if groups.shape != hidden.shape[:2] or attention.shape != groups.shape:
        raise ValueError('Group/attention shape mismatch')
    for row, length in enumerate(lengths.tolist()):
        if bool((groups[row, :length] != 0).any()) or int(groups[row, length]) == 0:
            raise ValueError('Prompt boundary does not match frozen answer groups')
        if not bool((attention[row, :length + 1] == 1).all()):
            raise ValueError('Prompt-last and first answer cannot be padding')
    positions = lengths.long() - 1
    return hidden[torch.arange(hidden.shape[0], device=hidden.device), positions], positions


def auxiliary_hidden_loss(hidden, aux_head, batch):
    states, positions = prompt_states(hidden, batch)
    if any(p.dtype != torch.float32 or not p.requires_grad for p in aux_head.parameters()):
        raise ValueError('Auxiliary head must remain trainable FP32')
    targets = torch.as_tensor(batch['support_target'], device=hidden.device, dtype=torch.float32).reshape(-1)
    if targets.shape != (hidden.shape[0],) or not bool(((targets == 0) | (targets == 1)).all()):
        raise ValueError('One GT-derived binary target 0/1 is required per row')
    logits = aux_head(states).reshape(-1)
    if logits.shape != targets.shape:
        raise ValueError('Binary head must return one logit per row')
    with torch.autocast(device_type=hidden.device.type, enabled=False):
        loss = F.binary_cross_entropy_with_logits(logits.float(), targets, reduction='mean')
    return loss, dict(aux_position=positions.detach().cpu().tolist(), aux_weight=1.0)


def backbone_loss(model, batch, aux_head=None, chunk_tokens=16):
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    if not hasattr(base, 'model') or not hasattr(base, 'lm_head'):
        raise TypeError('Expected pinned Qwen3.5 conditional-generation backbone/head')
    if any(p.requires_grad for p in base.lm_head.parameters()):
        raise ValueError('LM head must remain frozen')
    outputs = base.model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], use_cache=False, return_dict=True)
    hidden = outputs.last_hidden_state if hasattr(outputs, 'last_hidden_state') else outputs[0]
    main, info = segmented_hidden_loss(hidden, base.lm_head, batch['input_ids'], batch['groups'], chunk_tokens)
    info = dict(info, main_loss=float(main.detach()), aux_loss=0.0, aux_weight=0.0)
    if aux_head is None:
        return main, info
    auxiliary, aux_info = auxiliary_hidden_loss(hidden, aux_head, batch)
    info.update(aux_info)
    info['aux_loss'] = float(auxiliary.detach())
    return main + auxiliary, info
