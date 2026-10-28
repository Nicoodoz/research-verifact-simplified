"""Real tiny causal-attention/LoRA CPU checks; no clinical efficacy claims.

No 9B model, CUDA initialization, network, cloud connection or paid call.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '105_brief_supervision'))
import common105 as c
from data105 import training_plan, validate_cursor
from loss105 import backbone_loss as original_loss
from loss107 import make_aux_head, prompt_states, auxiliary_hidden_loss, backbone_loss
import checkpoint107 as ckpt


class TinyLoRA(nn.Module):
    def __init__(self, width=8, rank=2):
        super().__init__()
        self.base = nn.Linear(width, width, bias=False)
        self.base.requires_grad_(False)
        self.lora_A = nn.Parameter(torch.empty(rank, width))
        nn.init.kaiming_uniform_(self.lora_A, a=5 ** .5)
        self.lora_B = nn.Parameter(torch.zeros(width, rank))

    def forward(self, x):
        return self.base(x) + F.linear(F.linear(x, self.lora_A), self.lora_B) * 2


class TinyCausalBackbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(19, 8)
        self.embedding.requires_grad_(False)
        self.q = TinyLoRA()
        self.k = nn.Linear(8, 8, bias=False)
        self.k.requires_grad_(False)
        self.v = TinyLoRA()
        self.calls = 0

    def forward(self, input_ids, attention_mask=None, **kwargs):
        self.calls += 1
        x = self.embedding(input_ids)
        # A real causal attention operation, not a state lookup or fake loss.
        q, k, v = (layer(x).unsqueeze(1) for layer in (self.q, self.k, self.v))
        attended = F.scaled_dot_product_attention(q, k, v, dropout_p=0., is_causal=True).squeeze(1)
        return SimpleNamespace(last_hidden_state=(x + attended).tanh())


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = TinyCausalBackbone()
        self.lm_head = nn.Linear(8, 19, bias=False)
        self.lm_head.requires_grad_(False)

    def save_pretrained(self, folder, safe_serialization=True):
        torch.save(self.state_dict(), Path(folder) / 'toy_adapter.pt')


def batch(target=1, value_tokens=1):
    ids = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
    return dict(input_ids=ids, attention_mask=torch.ones_like(ids),
                groups=torch.tensor([[0] * 5 + [2] + [1] * value_tokens + [2] * (4 - value_tokens)]),
                prompt_tokens=5, support_target=target)


def fresh(arm='support_aux'):
    torch.manual_seed(103027)
    np.random.seed(103027)
    random.seed(103027)
    model = TinyModel()
    head = make_aux_head(8, seed=103028) if arm == 'support_aux' else None
    parameters = [p for p in model.parameters() if p.requires_grad]
    if head is not None:
        parameters += list(head.parameters())
    optimizer = torch.optim.AdamW(parameters, lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0.)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.)
    return model, head, optimizer, scheduler


class CPUChecks107(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise RuntimeError('CPU tests require an uninitialized CUDA runtime')

    def test_identical_fresh_lora_head_local_rng_and_optimizer(self):
        left, _, _, _ = fresh('label_only')
        rng = torch.get_rng_state().clone()
        py = random.getstate()
        numpy_rng = np.random.get_state()
        head = make_aux_head(8, seed=103028)
        torch.testing.assert_close(torch.get_rng_state(), rng, atol=0, rtol=0)
        self.assertEqual(random.getstate(), py)
        np.testing.assert_equal(np.random.get_state(), numpy_rng)
        right, actual, optimizer, _ = fresh('support_aux')
        for name, value in left.state_dict().items():
            torch.testing.assert_close(value, right.state_dict()[name], atol=0, rtol=0)
        for a, b in zip(head.parameters(), actual.parameters()):
            torch.testing.assert_close(a, b, atol=0, rtol=0)
            self.assertEqual(a.dtype, torch.float32)
        ckpt.assert_head_optimized(optimizer, actual)
        wrong = torch.optim.AdamW([p for p in right.parameters() if p.requires_grad], lr=1e-4)
        with self.assertRaises(ValueError):
            ckpt.assert_head_optimized(wrong, actual)

    def test_original_105_main_value_gradient_identical_and_single_forward(self):
        for tokens in (1, 2, 3):
            for arm in ('label_only', 'support_aux'):
                current, head, _, _ = fresh(arm)
                original = deepcopy(current)
                data = batch(value_tokens=tokens)
                got, info = backbone_loss(current, data, head, chunk_tokens=2)
                expected, old_info = original_loss(original, data, chunk_tokens=2)
                self.assertEqual(current.model.calls, 1)
                self.assertEqual(info['verdict_tokens'], old_info['verdict_tokens'])
                self.assertEqual(info['main_loss'], float(expected.detach()))
                if head is None:
                    torch.testing.assert_close(got, expected, atol=0, rtol=0)
                    ga = torch.autograd.grad(got, [p for p in current.parameters() if p.requires_grad])
                    ge = torch.autograd.grad(expected, [p for p in original.parameters() if p.requires_grad])
                    for a, e in zip(ga, ge):
                        torch.testing.assert_close(a, e, atol=0, rtol=0)
                else:
                    self.assertAlmostEqual(float(got.detach()), info['main_loss'] + info['aux_loss'], places=6)
                    self.assertEqual(info['aux_position'], [4])
                    self.assertEqual(info['aux_weight'], 1.)

    def test_no_answer_leak_and_invalid_boundaries_fail_closed(self):
        model, head, _, _ = fresh()
        one = batch()
        two = deepcopy(one)
        two['input_ids'][:, 5:] = torch.tensor([[18, 17, 16, 15, 14]])
        first = model.model(**{k: one[k] for k in ('input_ids', 'attention_mask')}).last_hidden_state
        second = model.model(**{k: two[k] for k in ('input_ids', 'attention_mask')}).last_hidden_state
        a, _ = prompt_states(first, one)
        b, _ = prompt_states(second, two)
        torch.testing.assert_close(a, b, atol=0, rtol=0)
        torch.testing.assert_close(head(a), head(b), atol=0, rtol=0)
        prefix = model.model(input_ids=one['input_ids'][:, :5]).last_hidden_state[:, -1]
        torch.testing.assert_close(a, prefix, atol=2e-7, rtol=2e-7)
        for bad in (0, 6, 10, 5.0, True):
            data = dict(one, prompt_tokens=bad)
            with self.assertRaises(ValueError):
                auxiliary_hidden_loss(first, head, data)
        for target in (-1, .5, 2, float('nan')):
            with self.assertRaises(ValueError):
                auxiliary_hidden_loss(first, head, dict(one, support_target=target))

    def test_aux_only_backprop_reaches_lora_and_head_without_lm_loss(self):
        for target in (0, 1):
            model, head, optimizer, _ = fresh()
            data = batch(target=target)
            hidden = model.model(input_ids=data['input_ids'], attention_mask=data['attention_mask']).last_hidden_state
            loss, _ = auxiliary_hidden_loss(hidden, head, data)
            expected = F.binary_cross_entropy_with_logits(head(hidden[:, 4]).reshape(-1), torch.tensor([float(target)]))
            torch.testing.assert_close(loss, expected, atol=0, rtol=0)
            before = model.model.v.lora_B.detach().clone()
            loss.backward()
            self.assertGreater(float(model.model.v.lora_B.grad.abs().sum()), 0.)
            self.assertGreater(float(head.weight.grad.abs().sum()), 0.)
            self.assertIsNone(model.lm_head.weight.grad)
            optimizer.step()
            self.assertFalse(torch.equal(before, model.model.v.lora_B))
            optimizer.zero_grad(set_to_none=True)
            hidden = model.model(input_ids=data['input_ids']).last_hidden_state
            auxiliary_hidden_loss(hidden, head, data)[0].backward()
            self.assertGreater(float(model.model.v.lora_A.grad.abs().sum()), 0.)

    def test_head_bce_stay_fp32_inside_outer_bfloat16_autocast(self):
        model, head, _, _ = fresh()
        data = batch(target=0)
        with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
            hidden = model.model(input_ids=data['input_ids']).last_hidden_state
            logits = head(hidden[:, 4].to(torch.bfloat16))
            auxiliary, _ = auxiliary_hidden_loss(hidden, head, data)
        self.assertEqual(logits.dtype, torch.float32)
        self.assertEqual(auxiliary.dtype, torch.float32)
        auxiliary.backward()
        self.assertGreater(float(model.model.v.lora_B.grad.abs().sum()), 0.)
        self.assertEqual(head.weight.grad.dtype, torch.float32)

    def test_both_arms_196_twice_tail_exact_resume_all_rng(self):
        plan = training_plan([str(i) for i in range(196)], 2, 8)
        self.assertEqual(len(plan), 50)
        self.assertEqual([e['loss_divisor'] for e in plan if e['epoch_end']], [4, 4])
        self.assertEqual(plan[-1]['consumed'], 392)

        def advance(model, head, optimizer, scheduler, entries):
            for entry in entries:
                optimizer.zero_grad(set_to_none=True)
                for identifier in entry['ids']:
                    data = batch(target=int(identifier) % 2, value_tokens=1 + int(identifier) % 3)
                    data['input_ids'] = torch.randint(0, 19, data['input_ids'].shape)
                    scale = .1 + random.random() + np.random.random()
                    loss, _ = backbone_loss(model, data, head, chunk_tokens=2)
                    (loss * scale / entry['loss_divisor']).backward()
                torch.nn.utils.clip_grad_norm_([p for g in optimizer.param_groups for p in g['params']], 1.)
                optimizer.step()
                scheduler.step()

        for arm in ('label_only', 'support_aux'):
            full, full_head, fo, fs = fresh(arm)
            advance(full, full_head, fo, fs, plan)
            part, part_head, po, ps = fresh(arm)
            advance(part, part_head, po, ps, plan[:25])
            with tempfile.TemporaryDirectory() as tmp:
                fingerprint = {'task': 107, 'arm': arm, 'synthetic': True}
                ckpt.save(part, po, ps, tmp, 25, 196, fingerprint, part_head)
                resumed, resumed_head, ro, rs = fresh(arm)

                def restore(folder):
                    resumed.load_state_dict(torch.load(folder / 'toy_adapter.pt', weights_only=True))

                step, consumed, _ = ckpt.load(ro, rs, tmp, fingerprint, restore, resumed_head)
                advance(resumed, resumed_head, ro, rs, validate_cursor(plan, step, consumed))
                self.assertEqual(rs.last_epoch, 50)
                for name, value in full.state_dict().items():
                    torch.testing.assert_close(value, resumed.state_dict()[name], atol=0, rtol=0)
                if full_head is not None:
                    for a, b in zip(full_head.parameters(), resumed_head.parameters()):
                        torch.testing.assert_close(a, b, atol=0, rtol=0)
                final = ckpt.save(resumed, ro, rs, tmp, 50, 392, fingerprint, resumed_head)
                complete = c.read(final / 'checkpoint_complete.json')
                self.assertEqual('aux_head.pt' in complete['files'], arm == 'support_aux')
                final_step, final_consumed, _ = ckpt.load(ro, rs, tmp, fingerprint, restore, resumed_head)
                self.assertEqual(validate_cursor(plan, final_step, final_consumed), [])
                pointer = (Path(tmp) / 'resume.json').read_bytes()
                with patch.object(resumed, 'save_pretrained', side_effect=RuntimeError('simulated inactive-slot failure')):
                    with self.assertRaises(RuntimeError):
                        ckpt.save(resumed, ro, rs, tmp, 50, 392, fingerprint, resumed_head)
                self.assertEqual((Path(tmp) / 'resume.json').read_bytes(), pointer)
                if resumed_head is not None:
                    original_save = torch.save

                    def fail_head(value, path, *args, **kwargs):
                        if Path(path).name == 'aux_head.pt.tmp':
                            raise RuntimeError('simulated auxiliary-head write failure')
                        return original_save(value, path, *args, **kwargs)

                    with patch.object(ckpt.torch, 'save', side_effect=fail_head):
                        with self.assertRaises(RuntimeError):
                            ckpt.save(resumed, ro, rs, tmp, 50, 392, fingerprint, resumed_head)
                    self.assertEqual((Path(tmp) / 'resume.json').read_bytes(), pointer)
                    ckpt.load(ro, rs, tmp, fingerprint, restore, resumed_head)

    def test_checkpoint_head_corruption_and_arm_mismatch_rejected(self):
        model, head, optimizer, scheduler = fresh()
        with tempfile.TemporaryDirectory() as tmp:
            fingerprint = {'task': 107, 'arm': 'support_aux'}
            folder = ckpt.save(model, optimizer, scheduler, tmp, 0, 0, fingerprint, head)
            restore = lambda _: None
            with self.assertRaises(ValueError):
                ckpt.load(optimizer, scheduler, tmp, fingerprint, restore, None)
            path = folder / 'aux_head.pt'
            path.write_bytes(path.read_bytes() + b'corrupt')
            with self.assertRaises(ValueError):
                ckpt.load(optimizer, scheduler, tmp, fingerprint, restore, head)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CPUChecks107)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    initialized = torch.cuda.is_initialized()
    if args.report is not None:
        c.put(args.report, dict(task=107, scope='tiny_causal_attention_LoRA_CPU_implementation_only',
                               tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                               passed=result.wasSuccessful() and not initialized, cuda_initialized=initialized,
                               torch_version=str(torch.__version__),
                               clinical_text_in_report=False, target_model_loaded=False,
                               head_seed=103028, main_loss='unchanged_import_of_loss105.segmented_hidden_loss',
                               checks=['identical_fresh_LoRA_and_no_global_RNG_consumption', 'main_105_value_gradient_exact',
                                       'one_shared_backbone_forward', 'causal_prompt_last_answer_independence',
                                       'aux_only_gradient_reaches_LoRA_A_after_update_and_LoRA_B_from_start',
                                       'head_optimized_FP32_BCE_weight_one_including_outer_BF16_autocast', 'both_arms_196x2_tail4_exact_resume',
                                       'adapter_head_optimizer_scheduler_python_numpy_torch_RNG_restore',
                                       'interrupted_inactive_write_preserves_pointer', 'corrupt_head_rejected'],
                               limitation='CPU implementation tests do not prove 9B GPU behavior or classification improvement'))
    if initialized:
        raise RuntimeError('Tiny CPU tests unexpectedly initialized CUDA')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
