"""Necessary CPU checks for the new weighting and parent/child state boundary."""
from pathlib import Path
import json
import random
import sys
import tempfile
import unittest

import numpy as np
import torch
from safetensors.torch import load_file, save_file

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/107_support_aux'))
import checkpoint107 as checkpoint
from objective128 import class_weights, coefficients, restore_parent, EXPECTED_COUNTS


class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lora_B = torch.nn.Parameter(torch.tensor([.25, -.5]))

    def save_pretrained(self, folder, **_):
        Path(folder).mkdir(parents=True, exist_ok=True)
        save_file(self.state_dict(), str(Path(folder) / 'adapter_model.safetensors'))


def setup():
    model = Tiny()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=0.)
    sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda _: 1.)
    return model, opt, sch


class Checks(unittest.TestCase):
    def test_weighted_gradient_and_short_tail(self):
        weights = class_weights(EXPECTED_COUNTS)
        labels = {'a': 'Supported', 'b': 'Not Supported', 'c': 'Not Addressed'}
        coefs = coefficients(['a', 'b', 'c'], labels, weights)
        self.assertAlmostEqual(sum(coefs), 1.)
        self.assertEqual(coefficients(['c'], labels, weights), [1.])
        self.assertEqual(coefficients(['a', 'b', 'c'], labels, {k: 1. for k in weights}), [1/3]*3)
        a = torch.tensor([.3, -.1], requires_grad=True)
        b = a.detach().clone().requires_grad_()
        targets = [torch.tensor([1., 0.]), torch.tensor([0., 1.]), torch.tensor([-.5, -.5])]
        for c, target in zip(coefs, targets):
            (((a-target)**2).mean()*c).backward()
        (torch.stack([((b-target)**2).mean() for target in targets])*torch.tensor(coefs)).sum().backward()
        self.assertTrue(torch.allclose(a.grad, b.grad))
        self.assertGreater(float(a.grad.norm()), 0.)

    def test_parent_restore_and_separate_child_identity(self):
        torch.manual_seed(12); random.seed(12); np.random.seed(12)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, opt, sch = setup()
            model.lora_B.square().sum().backward(); opt.step(); sch.step(); opt.zero_grad(set_to_none=True)
            parent = checkpoint.save(model, opt, sch, root/'parent', 220, 1760, {'task': 120, 'fixed': 'parent'})
            manifest_bytes = (parent/'checkpoint_complete.json').read_bytes()
            manifest = json.loads(manifest_bytes)
            expected_draw = (torch.rand(2), random.random(), np.random.rand())
            branch, branch_opt, branch_sch = setup()
            def restore(folder):
                branch.load_state_dict(load_file(str(folder/'adapter_model.safetensors')))
            step, consumed, found = restore_parent(parent, branch_opt, branch_sch, restore,
                                                   manifest['files']['adapter_model.safetensors'])
            self.assertEqual((step, consumed), (220, 1760))
            self.assertTrue(torch.equal(model.lora_B, branch.lora_B))
            self.assertTrue(torch.equal(opt.state[model.lora_B]['exp_avg'], branch_opt.state[branch.lora_B]['exp_avg']))
            self.assertTrue(torch.equal(torch.rand(2), expected_draw[0]))
            self.assertEqual(random.random(), expected_draw[1]); self.assertEqual(np.random.rand(), expected_draw[2])
            fingerprint = {'task': 128, 'parent': found['fingerprint'], 'weighting': 'sqrt'}
            child = checkpoint.save(branch, branch_opt, branch_sch, root/'child', step, consumed, fingerprint)
            branch.lora_B.data.add_(1.)
            checkpoint.load(branch_opt, branch_sch, root/'child', fingerprint, restore)
            self.assertTrue(torch.equal(model.lora_B, branch.lora_B))
            self.assertEqual((parent/'checkpoint_complete.json').read_bytes(), manifest_bytes)
            self.assertEqual(json.loads((child/'checkpoint_complete.json').read_bytes())['fingerprint'], fingerprint)


if __name__ == '__main__':
    unittest.main()
