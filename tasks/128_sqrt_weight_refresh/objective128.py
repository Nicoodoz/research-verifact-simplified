"""Fixed example weights and explicit parent-state continuation for experiment128.

The token-level loss remains loss105.backbone_loss. These coefficients only
change its example-level weighting within an existing optimizer step.
"""
from collections import Counter
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common


EXPECTED_COUNTS = {'Supported': 2379, 'Not Supported': 243, 'Not Addressed': 323}


def class_weights(counts):
    if set(counts) != set(EXPECTED_COUNTS) or any(n <= 0 for n in counts.values()):
        raise ValueError('Three positive class counts required')
    return {label: math.sqrt(counts['Supported'] / count) for label, count in counts.items()}


def coefficients(ids, labels, weights):
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Expected a nonempty optimizer-step ID list without duplicates')
    values = [weights[labels[i]] for i in ids]
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Example weights must be finite and positive')
    total = sum(values)
    return [v / total for v in values]


def restore_parent(folder, optimizer, scheduler, restore_adapter, expected_adapter_sha):
    """Load the saved step220 as a parent, without relabeling its fingerprint.

    New rolling checkpoints get a separate128 fingerprint in the caller.
    Only the two files required for continuation are rehashed once here.
    """
    import numpy as np
    import torch
    folder = Path(folder)
    manifest = common.read(folder / 'checkpoint_complete.json')
    if (manifest['step'], manifest['consumed']) != (220, 1760):
        raise ValueError('Parent must be the actual120 step220, not a later rolling slot')
    if manifest.get('has_aux_head') is not False or manifest.get('checkpoint_version') != 107:
        raise ValueError('Unexpected parent checkpoint type')
    if manifest['files']['adapter_model.safetensors'] != expected_adapter_sha:
        raise ValueError('Parent adapter identity differs from frozen120 step220')
    for name in ('adapter_model.safetensors', 'training_state.pt'):
        if common.sha(folder / name) != manifest['files'][name]:
            raise ValueError('Parent continuation file differs: ' + name)
    state = torch.load(folder / 'training_state.pt', map_location='cpu', weights_only=False)
    if (state['step'], state['consumed'], state['fingerprint']) != (220, 1760, manifest['fingerprint']):
        raise ValueError('Parent optimizer cursor/fingerprint differs')
    if state.get('has_aux_head') is not False:
        raise ValueError('Auxiliary-head state is not allowed')
    restore_adapter(folder)
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    torch.set_rng_state(state['torch_rng'])
    random.setstate(state['python_rng'])
    np.random.set_state(state['numpy_rng'])
    if state['cuda_rng']:
        if not torch.cuda.is_available():
            raise RuntimeError('The real parent contains CUDA RNG; CUDA is required to resume it')
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return 220, 1760, manifest


def validate_training_rows(rows):
    counts = dict(Counter(row['GT'] for row in rows))
    if counts != EXPECTED_COUNTS or len(rows) != 2945 or len({r['id'] for r in rows}) != 2945:
        raise ValueError('Original120 training population changed')
    return class_weights(counts)
