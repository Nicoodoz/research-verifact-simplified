"""Three-token clinical classifier; no model, CUDA or network at import.

The original104 clinical instructions and full claim/reference are retained.
Only the output-format paragraph changes to A/B/C. A single causal backbone
forward supplies the last nonpadding prompt state; the frozen LM-head rows
for A/B/C supply three logits. Training and inference use the same restricted
three-class distribution, without JSON/EOS losses or token-length divisors.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

TASKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASKS / '104_supervision_evidence'))
import training104 as original

LABELS = ('Supported', 'Not Supported', 'Not Addressed')
if LABELS != tuple(original.LABELS):
    raise ValueError('The original three-class label schema changed')
CODES = ('A', 'B', 'C')
LABEL_TO_INDEX = {label: i for i, label in enumerate(LABELS)}
CODE_TO_LABEL = dict(zip(CODES, LABELS))
OUTPUT_RULE = (
    '4. Return exactly one letter and nothing else. Use this fixed mapping:\n'
    '   - A = Supported\n'
    '   - B = Not Supported\n'
    '   - C = Not Addressed\n'
    '   Output only A, B, or C.'
)


def _instructions() -> str:
    text = original.INSTRUCTIONS
    start = '\n4. '
    ending = '\n\n## Input JSON:\n'
    if text.count(start) != 1 or text.count(ending) != 1:
        raise ValueError('The104 instruction structure changed; review output substitution')
    retained, tail = text.split(start, 1)
    old_rule, remainder = tail.split(ending, 1)
    if not old_rule.startswith('Return a JSON object'):
        raise ValueError('Unexpected104 output paragraph; do not replace clinical definitions')
    return retained + '\n' + OUTPUT_RULE + ending + remainder


INSTRUCTIONS = _instructions()


def messages(claim: str, reference: str) -> list[dict[str, str]]:
    """Build from the full originals; no label or historical prediction argument."""
    old = original.messages(claim, reference)
    if not old[1]['content'].startswith(original.INSTRUCTIONS):
        raise ValueError('The104 message builder changed')
    payload = old[1]['content'][len(original.INSTRUCTIONS):]
    return [dict(old[0]), {'role': 'user', 'content': INSTRUCTIONS + payload}]


def prompt_ids(tokenizer: Any, row: Mapping[str, Any]) -> list[int]:
    """Rebuild only from claim/reference; old answer/messages/GT are not inputs."""
    ids = tokenizer.apply_chat_template(
        messages(row['claim'], row['reference']), tokenize=True,
        add_generation_prompt=True, enable_thinking=False, reasoning_effort='low',
    )
    if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
        raise ValueError('Expected nonempty flat tokenizer IDs')
    return ids


def label_token_ids(tokenizer: Any) -> tuple[int, int, int]:
    """Verify the actual tokenizer supplies three distinct, lossless single tokens."""
    result = []
    for code in CODES:
        ids = tokenizer.encode(code, add_special_tokens=False)
        if len(ids) != 1 or type(ids[0]) is not int or ids[0] < 0:
            raise ValueError('Each class code must encode as exactly one token: ' + code)
        if tokenizer.decode(ids, skip_special_tokens=False) != code:
            raise ValueError('Class code must decode losslessly: ' + code)
        if ids[0] in getattr(tokenizer, 'all_special_ids', ()):
            raise ValueError('A class code cannot be a special token')
        result.append(ids[0])
    if len(set(result)) != 3:
        raise ValueError('A/B/C require distinct token IDs')
    return tuple(result)


def last_nonpad_positions(attention_mask: Any):
    """Absolute indices of the last1, valid for both left and right padding."""
    import torch
    if attention_mask.ndim != 2 or attention_mask.shape[1] == 0:
        raise ValueError('A nonempty [batch, sequence] mask is required')
    if not bool(((attention_mask == 0) | (attention_mask == 1)).all()):
        raise ValueError('Attention mask must be binary')
    present = attention_mask.to(torch.bool)
    if not bool(present.any(dim=1).all()):
        raise ValueError('A prompt cannot be entirely padding')
    positions = torch.arange(present.shape[1], device=present.device, dtype=torch.long)
    return positions.expand_as(present).masked_fill(~present, -1).amax(dim=1)


def last_nonpad_hidden(hidden: Any, attention_mask: Any):
    import torch
    if hidden.ndim != 3 or tuple(hidden.shape[:2]) != tuple(attention_mask.shape):
        raise ValueError('Hidden states and attention mask must align')
    positions = last_nonpad_positions(attention_mask).to(hidden.device)
    return hidden[torch.arange(hidden.shape[0], device=hidden.device), positions]


def _checked_code_ids(code_ids: Sequence[int], vocab_size: int) -> tuple[int, int, int]:
    values = tuple(code_ids)
    if len(values) != 3 or len(set(values)) != 3:
        raise ValueError('Expected three distinct class-token IDs in A/B/C order')
    if any(type(i) is not int or not 0 <= i < vocab_size for i in values):
        raise ValueError('Class-token ID outside the frozen output vocabulary')
    return values


def project_three_rows(states: Any, lm_head: Any, code_ids: Sequence[int]):
    """Equivalent to lm_head(states)[:, code_ids], without the full vocabulary."""
    import torch
    from torch.nn import functional as F
    if states.ndim != 2 or not hasattr(lm_head, 'weight') or lm_head.weight.ndim != 2:
        raise ValueError('Expected [batch, hidden] states and a linear LM head')
    if any(p.requires_grad for p in lm_head.parameters()):
        raise ValueError('LM head must remain frozen; only backbone/LoRA is optimized')
    ids = _checked_code_ids(code_ids, lm_head.weight.shape[0])
    selected = torch.tensor(ids, dtype=torch.long, device=lm_head.weight.device)
    weight = lm_head.weight.index_select(0, selected).detach()
    bias = getattr(lm_head, 'bias', None)
    bias = None if bias is None else bias.index_select(0, selected).detach()
    # Three rows are cheap; FP32 logits/CE avoid precision loss without a giant
    # [sequence,vocab] tensor. Casting preserves the gradient into the states.
    with torch.autocast(device_type=states.device.type, enabled=False):
        return F.linear(states.float(), weight.float(), None if bias is None else bias.float())


def restricted_logits(model: Any, batch: Mapping[str, Any], code_ids: Sequence[int]):
    """One backbone forward, reading no teacher-forced answer or GT."""
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    if not hasattr(base, 'model') or not hasattr(base, 'lm_head'):
        raise TypeError('Expected the Qwen conditional-generation backbone and frozen head')
    ids, mask = batch['input_ids'], batch['attention_mask']
    if ids.ndim != 2 or tuple(ids.shape) != tuple(mask.shape):
        raise ValueError('Input IDs and mask must be aligned [batch, sequence] tensors')
    # Explicit kwargs prevent accidental forwarding of GT/answer metadata.
    kwargs = dict(input_ids=ids, attention_mask=mask, use_cache=False, return_dict=True)
    if 'position_ids' in batch:
        kwargs['position_ids'] = batch['position_ids']
    result = base.model(**kwargs)
    hidden = result.last_hidden_state if hasattr(result, 'last_hidden_state') else result[0]
    states = last_nonpad_hidden(hidden, mask)
    return project_three_rows(states, base.lm_head, code_ids)


def loss_from_logits(logits: Any, targets: Any, reduction: str = 'mean'):
    """Ordinary three-class CE; no sequence/token-length normalization."""
    import torch
    from torch.nn import functional as F
    if logits.ndim != 2 or logits.shape[1] != 3:
        raise ValueError('Expected [batch,3] class logits')
    target = torch.as_tensor(targets, device=logits.device)
    integer_dtypes = (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8)
    if target.dtype not in integer_dtypes or target.ndim != 1 or len(target) != len(logits):
        raise ValueError('GT targets must be one integer class index per prompt')
    if not bool(((target >= 0) & (target < 3)).all()):
        raise ValueError('GT index must be0,1,2 in S/NS/NA order')
    if reduction not in {'mean', 'sum', 'none'}:
        raise ValueError('Unsupported loss reduction')
    with torch.autocast(device_type=logits.device.type, enabled=False):
        return F.cross_entropy(logits.float(), target.long(), reduction=reduction)


def classification_loss(model: Any, batch: Mapping[str, Any], code_ids: Sequence[int],
                        targets: Any, reduction: str = 'mean'):
    """Return (loss, logits); exactly one backbone call and normal autograd."""
    logits = restricted_logits(model, batch, code_ids)
    return loss_from_logits(logits, targets, reduction), logits


def predictions_from_logits(logits: Any) -> list[dict[str, Any]]:
    import torch
    if logits.ndim != 2 or logits.shape[1] != 3 or not bool(torch.isfinite(logits).all()):
        raise ValueError('Expected finite [batch,3] class logits')
    with torch.inference_mode():
        probabilities = torch.softmax(logits.float(), dim=-1).detach().cpu().tolist()
        indices = logits.argmax(dim=-1).detach().cpu().tolist()
    records = []
    for index, probs in zip(indices, probabilities):
        verdict = LABELS[index]
        records.append(dict(
            class_index=index, code=CODES[index], verdict=verdict,
            probabilities=dict(zip(LABELS, probs)), probabilities_calibrated=False,
            probability_scope='conditional_on_fixed_A_B_C',
            content=json.dumps({'verdict': verdict}, ensure_ascii=False, separators=(',', ':')),
            output_is_deterministic_label_mapping=True,
        ))
    return records


def predict(model: Any, batch: Mapping[str, Any], code_ids: Sequence[int]):
    """GT-free inference; caller controls model.eval()/training mode."""
    import torch
    with torch.inference_mode():
        return predictions_from_logits(restricted_logits(model, batch, code_ids))


def self_test(tokenizer_dir: str | None = None) -> dict[str, Any]:
    """Tiny CPU-only forward/backward checks. No optimizer or9B is loaded."""
    import torch
    from torch import nn
    from types import SimpleNamespace
    torch.manual_seed(116)
    masks = torch.tensor([[0, 0, 1, 1], [1, 1, 1, 0], [0, 1, 1, 0]])
    assert last_nonpad_positions(masks).tolist() == [3, 2, 2]
    h = torch.arange(3 * 4 * 5).reshape(3, 4, 5).float()
    assert torch.equal(last_nonpad_hidden(h, masks), torch.stack([h[0, 3], h[1, 2], h[2, 2]]))
    try:
        last_nonpad_positions(torch.zeros(1, 4))
        raise AssertionError('All-padding mask was accepted')
    except ValueError:
        pass

    class SmallBackbone(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(11, 5)
            self.calls = 0
        def forward(self, input_ids, attention_mask, use_cache, return_dict):
            assert not use_cache and return_dict
            self.calls += 1
            return SimpleNamespace(last_hidden_state=self.embedding(input_ids))

    class SmallModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.model = SmallBackbone()
            self.lm_head = nn.Linear(5, 11, bias=True)
            self.lm_head.requires_grad_(False)

    model = SmallModel()
    batch = dict(input_ids=torch.tensor([[0, 0, 2, 3], [4, 5, 6, 0], [0, 7, 8, 0]]),
                 attention_mask=masks, GT=['ignored', 'ignored', 'ignored'])
    ids = (1, 5, 9)
    logits = restricted_logits(model, batch, ids)
    assert model.model.calls == 1
    states = last_nonpad_hidden(model.model.embedding(batch['input_ids']), masks)
    expected = model.lm_head(states).index_select(1, torch.tensor(ids))
    assert torch.allclose(logits, expected, atol=1e-6, rtol=1e-6)
    with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
        under_autocast = restricted_logits(model, batch, ids)
    assert under_autocast.dtype == torch.float32
    assert torch.allclose(under_autocast, logits, atol=1e-6, rtol=1e-6)
    model.model.calls = 0
    loss, _ = classification_loss(model, batch, ids, [0, 1, 2])
    assert model.model.calls == 1
    loss.backward()
    assert model.model.embedding.weight.grad is not None
    assert bool(model.model.embedding.weight.grad.abs().sum() > 0)
    assert all(p.grad is None for p in model.lm_head.parameters())
    model.eval()
    records = predict(model, batch, ids)
    assert len(records) == 3 and all(r['verdict'] in LABELS for r in records)
    assert all(abs(sum(r['probabilities'].values()) - 1) < 1e-6 for r in records)
    assert all(not r['probabilities_calibrated'] for r in records)
    assert all(json.loads(r['content']) == {'verdict': r['verdict']} for r in records)

    claim, reference = 'Synthetic claim with "quotes".', 'Synthetic reference.\nSecond complete line.'
    built = messages(claim, reference)
    assert built[0] == {'role': 'system', 'content': original.SYSTEM}
    payload = json.loads(built[1]['content'].split('## Input JSON:\n', 1)[1])
    assert payload == {'text': claim, 'reference': reference}
    assert INSTRUCTIONS.split('\n4. ', 1)[0] == original.INSTRUCTIONS.split('\n4. ', 1)[0]
    assert 'Return a JSON object' not in INSTRUCTIONS and OUTPUT_RULE in INSTRUCTIONS
    assert 'Optional keys' not in INSTRUCTIONS

    class TestTokenizer:
        def encode(self, text, add_special_tokens=False):
            assert not add_special_tokens
            return [CODES.index(text) + 3]
        def decode(self, values, skip_special_tokens=False):
            return CODES[values[0] - 3]
        def apply_chat_template(self, msgs, tokenize, **kwargs):
            assert tokenize and kwargs['add_generation_prompt'] and not kwargs['enable_thinking']
            return list(json.dumps(msgs, ensure_ascii=False).encode('utf-8'))
    tokenizer = TestTokenizer()
    assert label_token_ids(tokenizer) == (3, 4, 5)
    a = prompt_ids(tokenizer, dict(claim=claim, reference=reference, GT='Supported'))
    b = prompt_ids(tokenizer, dict(claim=claim, reference=reference, GT='Not Addressed', answer='ignored'))
    assert a == b
    actual_ids = None
    if tokenizer_dir:
        sys.path.insert(0, str(TASKS / '105_brief_supervision'))
        from tokenizer_cpu105 import CPUPinnedTokenizer
        actual = CPUPinnedTokenizer(tokenizer_dir)
        actual_ids = label_token_ids(actual)
        assert prompt_ids(actual, dict(claim=claim, reference=reference))
    assert not torch.cuda.is_initialized(), 'Self-test must not initialize CUDA'
    return dict(PASS=True, last_absolute_nonpad_positions=True, left_and_right_padding=True,
                three_rows_equal_full_projection=True, one_backbone_forward=True,
                three_row_projection_stays_FP32_under_autocast=True,
                gradient_to_small_backbone=True, frozen_head_no_gradient=True,
                original_clinical_definitions=True, only_new_output_rule=True,
                full_claim_reference_preserved=True, GT_not_in_prompt=True,
                probabilities_not_calibrated=True, actual_class_token_ids=actual_ids,
                CPU_only=True, no_model_weights_loaded=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--tokenizer-dir', help='Optional existing tokenizer files only; no model load')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.tokenizer_dir), ensure_ascii=False))
    else:
        parser.print_help()
