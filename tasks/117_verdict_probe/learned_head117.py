"""Differentiable continuation of117's learned linear probe.

No model loading, GPU work, or training starts on import.  Callers own the
training schedule and optimizer.  Keep the small head in FP32 even when the
backbone uses BF16.  The fixed JSON prefix contains no class label.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/104_supervision_evidence'))
import training104 as original

LABELS = tuple(original.LABELS)

PREFIX_TEXT = '{"verdict":"'
PREFIX_IDS = (4754, 415, 8217, 3147)
REPRESENTATIONS = ('verdict_prefix', 'prompt_end')


def prompt_ids(tokenizer, row: dict) -> list[int]:
    """Match extract117: original prompt followed only by its common prefix."""
    tokens = tokenizer.encode(PREFIX_TEXT, add_special_tokens=False)
    if tuple(tokens) != PREFIX_IDS:
        raise ValueError('Tokenizer differs from the frozen117 prefix encoding')
    # Deliberately pass no GT, answer, historic verdict, patient or role.
    result = original.prompt_ids(tokenizer, dict(claim=row['claim'],
                                                reference=row['reference']))
    return result + list(PREFIX_IDS)


def last_positions(attention_mask: torch.Tensor) -> torch.Tensor:
    if attention_mask.ndim != 2 or not attention_mask.shape[1]:
        raise ValueError('Expected a nonempty two-dimensional attention mask')
    if not bool(((attention_mask == 0) | (attention_mask == 1)).all()):
        raise ValueError('Attention mask must be binary')
    valid = attention_mask.bool()
    if not bool(valid.any(dim=1).all()):
        raise ValueError('An all-padding row has no decision position')
    positions = torch.arange(valid.shape[1], device=valid.device)
    return positions.expand_as(valid).masked_fill(~valid, -1).amax(dim=1)


def check_prefix(input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Reject teacher-forced labels after the fixed prefix; handle both padding sides."""
    if input_ids.ndim != 2 or input_ids.shape != attention_mask.shape:
        raise ValueError('Input IDs and attention mask must be aligned [batch,sequence]')
    ends = last_positions(attention_mask).to(input_ids.device)
    offsets = torch.arange(len(PREFIX_IDS), device=input_ids.device)
    positions = ends[:, None] - len(PREFIX_IDS) + 1 + offsets[None, :]
    if bool((positions < 0).any()):
        raise ValueError('Input is shorter than the common verdict prefix')
    actual = input_ids.gather(1, positions)
    expected = torch.tensor(PREFIX_IDS, device=input_ids.device).expand_as(actual)
    if not torch.equal(actual, expected):
        raise ValueError('Input must end at the fixed prefix, before any true answer')
    if not bool(attention_mask.to(input_ids.device).gather(1, positions).bool().all()):
        raise ValueError('The common verdict prefix must not contain padding')
    return ends


class LearnedHead(nn.Module):
    """Frozen training-only StandardScaler plus trainable three-class affine head."""

    def __init__(self, coef, intercept, mean, scale, representation='verdict_prefix'):
        super().__init__()
        if representation not in REPRESENTATIONS:
            raise ValueError('Unknown117 feature position')
        coef = torch.as_tensor(np.array(coef, copy=True), dtype=torch.float32)
        intercept = torch.as_tensor(np.array(intercept, copy=True), dtype=torch.float32)
        mean = torch.as_tensor(np.array(mean, copy=True), dtype=torch.float32)
        scale = torch.as_tensor(np.array(scale, copy=True), dtype=torch.float32)
        width = mean.numel()
        if (mean.ndim != 1 or scale.shape != mean.shape or coef.shape != (3, width)
                or intercept.shape != (3,) or not bool((scale > 0).all())):
            raise ValueError('Invalid scaler or three-class head dimensions')
        if not all(bool(torch.isfinite(x).all()) for x in (coef, intercept, mean, scale)):
            raise ValueError('Scaler and head must be finite')
        self.representation = representation
        self.register_buffer('mean', mean)
        self.register_buffer('scale', scale)
        self.linear = nn.Linear(width, 3, bias=True, dtype=torch.float32)
        with torch.no_grad():
            self.linear.weight.copy_(coef)
            self.linear.bias.copy_(intercept)

    @classmethod
    def from_npz(cls, path: str | Path, device=None) -> 'LearnedHead':
        with np.load(path, allow_pickle=False) as saved:
            classes = tuple(np.asarray(saved['classes']).astype(str).tolist())
            if classes != tuple(LABELS):
                raise ValueError('Saved class order differs from the original project labels')
            representation = str(np.asarray(saved['representation']).item())
            result = cls(saved['coef'], saved['intercept'], saved['mean'],
                         saved['scale'], representation)
        return result.to(device=device) if device is not None else result

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        if states.ndim != 2 or states.shape[1] != self.mean.numel():
            raise ValueError('Expected [batch,feature_width] decision states')
        if states.device != self.linear.weight.device:
            raise ValueError('Head and decision states must be on the same device')
        if any(p.dtype != torch.float32 for p in self.parameters()):
            raise ValueError('Keep the learned head in FP32; move device without BF16 cast')
        with torch.autocast(device_type=states.device.type, enabled=False):
            standardized = (states.float() - self.mean.float()) / self.scale.float()
            return F.linear(standardized, self.linear.weight, self.linear.bias)

    def save_npz(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.tmp')
        with temporary.open('wb') as stream:
            np.savez_compressed(
                stream, coef=self.linear.weight.detach().float().cpu().numpy(),
                intercept=self.linear.bias.detach().float().cpu().numpy(),
                mean=self.mean.detach().float().cpu().numpy(),
                scale=self.scale.detach().float().cpu().numpy(),
                classes=np.asarray(LABELS), representation=np.asarray(self.representation))
        temporary.replace(path)


def decision_states(model, batch: dict, representation: str = 'verdict_prefix'):
    """One backbone call; explicit arguments cannot forward labels or answers."""
    if representation not in REPRESENTATIONS:
        raise ValueError('Unknown decision position')
    ids, mask = batch['input_ids'], batch['attention_mask']
    ends = check_prefix(ids, mask)
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    backbone = base.model if hasattr(base, 'model') else base
    kwargs = dict(input_ids=ids, attention_mask=mask, use_cache=False, return_dict=True)
    if 'position_ids' in batch:
        kwargs['position_ids'] = batch['position_ids']
    result = backbone(**kwargs)
    hidden = result.last_hidden_state if hasattr(result, 'last_hidden_state') else result[0]
    if hidden.ndim != 3 or hidden.shape[:2] != ids.shape:
        raise ValueError('Backbone states must match input IDs')
    positions = ends if representation == 'verdict_prefix' else ends - len(PREFIX_IDS)
    if bool((positions < 0).any()):
        raise ValueError('Missing original prompt before the verdict prefix')
    rows = torch.arange(ids.shape[0], device=hidden.device)
    return hidden[rows, positions.to(hidden.device)]


def logits(model, head: LearnedHead, batch: dict) -> torch.Tensor:
    return head(decision_states(model, batch, head.representation))


def target_indices(targets, device, count: int) -> torch.Tensor:
    if isinstance(targets, (list, tuple)) and all(isinstance(v, str) for v in targets):
        lookup = {label: i for i, label in enumerate(LABELS)}
        try:
            values = [lookup[label] for label in targets]
        except KeyError as error:
            raise ValueError('Unknown original GT label') from error
        result = torch.tensor(values, device=device, dtype=torch.long)
    else:
        result = torch.as_tensor(targets, device=device)
        if result.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64,
                                torch.uint8):
            raise ValueError('Targets must be original labels or integer class indices')
        result = result.long()
    if result.shape != (count,) or not bool(((result >= 0) & (result < 3)).all()):
        raise ValueError('Expected one original three-class target per sample')
    return result


def loss_from_logits(scores, targets, reduction: str = 'mean', class_weights=None):
    """Per-example weighted CE, with an ordinary batch mean.

    Class weights should have mean1 over the full training sample distribution
    (e.g. N/(K*class_count)).  Never renormalize by the current microbatch's
    weights: doing so would cancel weighting when microbatch size is1.
    """
    if reduction not in ('mean', 'sum', 'none'):
        raise ValueError('Reduction must be mean, sum or none')
    indices = target_indices(targets, scores.device, scores.shape[0])
    weight = None if class_weights is None else torch.as_tensor(
        class_weights, device=scores.device, dtype=torch.float32)
    if weight is not None and (weight.shape != (3,) or not bool((weight > 0).all())
                               or not bool(torch.isfinite(weight).all())):
        raise ValueError('Class weights must be three finite positive values')
    with torch.autocast(device_type=scores.device.type, enabled=False):
        per_example = F.cross_entropy(scores.float(), indices, reduction='none')
        if weight is not None:
            per_example = per_example * weight[indices]
        if reduction == 'mean':
            return per_example.mean()
        if reduction == 'sum':
            return per_example.sum()
        return per_example


def classification_loss(model, head: LearnedHead, batch: dict, targets,
                        reduction: str = 'mean', class_weights=None):
    """Ordinary weighted CE; gradients reach both the head and backbone/LoRA."""
    scores = logits(model, head, batch)
    loss = loss_from_logits(scores, targets, reduction, class_weights)
    return loss, scores


def self_test() -> dict:
    """CPU geometry and gradients only, not an efficacy experiment."""
    from types import SimpleNamespace
    from fit_probe117 import predict_head

    torch.manual_seed(117)
    rng = np.random.default_rng(117)
    single_scores = torch.tensor([[.4, -.2, .1]], requires_grad=True)
    unweighted = loss_from_logits(single_scores, ['Not Supported'])
    weight = [.5, 2., .5]
    weighted = loss_from_logits(single_scores, ['Not Supported'], class_weights=weight)
    if not torch.allclose(weighted, 2 * unweighted):
        raise AssertionError('Microbatch1 must retain its class weight')
    ordinary_gradient = torch.autograd.grad(unweighted, single_scores, retain_graph=True)[0]
    weighted_gradient = torch.autograd.grad(weighted, single_scores)[0]
    if not torch.allclose(weighted_gradient, 2 * ordinary_gradient):
        raise AssertionError('Microbatch1 gradient must retain its class weight')
    for reduction in ('sum', 'none'):
        value = loss_from_logits(single_scores, ['Not Supported'], reduction, weight)
        expected = 2 * unweighted.detach()
        if not torch.allclose(value, expected.expand_as(value)):
            raise AssertionError('Weighted sum/none must retain per-example weight')
    arrays = dict(coef=rng.normal(0, .2, (3, 6)), intercept=rng.normal(0, .1, 3),
                  mean=rng.normal(0, .3, 6), scale=rng.uniform(.8, 1.2, 6),
                  classes=np.asarray(LABELS), representation=np.asarray('verdict_prefix'))
    x = rng.normal(0, .4, (7, 6)).astype(np.float32)
    with tempfile.TemporaryDirectory(prefix='learned_head117_') as temporary:
        path = Path(temporary) / 'fit_head.npz'
        np.savez_compressed(path, **arrays)
        head = LearnedHead.from_npz(path)
        scores = head(torch.from_numpy(x))
        expected_label, expected_probability = predict_head(arrays, x)
        actual_probability = scores.softmax(dim=-1).detach().numpy()
        if not np.allclose(expected_probability, actual_probability, atol=1e-6, rtol=1e-6):
            raise AssertionError('FP32 head differs from saved sklearn geometry')
        if not np.array_equal(np.asarray(LABELS)[scores.argmax(-1).numpy()], expected_label):
            raise AssertionError('Original class order changed')
        path = Path(temporary) / 'saved_head.npz'
        head.save_npz(path)
        restored = LearnedHead.from_npz(path)
        if not torch.equal(restored(torch.from_numpy(x)), scores):
            raise AssertionError('Head checkpoint does not restore exact FP32 logits')

        class Backbone(nn.Module):
            def __init__(self):
                super().__init__()
                self.embedding = nn.Embedding(10000, 6)
                self.embedding.weight.requires_grad_(False)
                self.lora_A = nn.Parameter(torch.randn(6, 2) * .1)
                self.lora_B = nn.Parameter(torch.randn(2, 6) * .1)
                self.calls = 0
            def forward(self, input_ids, attention_mask, use_cache, return_dict):
                if use_cache or not return_dict:
                    raise AssertionError('Unexpected backbone call contract')
                self.calls += 1
                h = (self.embedding(input_ids) * attention_mask[..., None]).cumsum(1)
                return SimpleNamespace(last_hidden_state=h + h @ self.lora_A @ self.lora_B)

        backbone = Backbone()
        batch = dict(input_ids=torch.tensor([[0, 0, 11, 12, *PREFIX_IDS],
                                             [21, 22, 23, *PREFIX_IDS, 0]]),
                     attention_mask=torch.tensor([[0, 0, 1, 1, 1, 1, 1, 1],
                                                  [1, 1, 1, 1, 1, 1, 1, 0]]))
        loss, actual = classification_loss(backbone, restored, batch,
                                            ['Supported', 'Not Addressed'])
        loss.backward()
        if backbone.calls != 1 or actual.dtype != torch.float32:
            raise AssertionError('Require one shared backbone call and FP32 scores')
        gradients = [restored.linear.weight.grad, restored.linear.bias.grad,
                     backbone.lora_A.grad, backbone.lora_B.grad]
        if not all(g is not None and bool(torch.isfinite(g).all()) and
                   bool(g.abs().sum() > 0) for g in gradients):
            raise AssertionError('Head and LoRA must both receive finite nonzero gradients')
        bad = dict(batch, input_ids=batch['input_ids'].clone())
        bad['input_ids'][0, -1] = 17
        try:
            logits(backbone, restored, bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Answer-appended input was accepted')
        if backbone.calls != 1:
            raise AssertionError('Bad input reached the backbone')
        return dict(status='PASS', numpy_geometry_atol=1e-6, FP32_head=True,
                    restored_logits_identical=True, one_backbone_call=True,
                    head_gradient=True, LoRA_gradient=True,
                    microbatch1_weight_scales_loss_and_gradient=True,
                    left_right_padding=True, answer_boundary_checked=True,
                    only_implementation_checked=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if not args.self_test:
        parser.error('This module only provides reusable functions; use --self-test for CPU checks')
    print(json.dumps(self_test(), ensure_ascii=False))
