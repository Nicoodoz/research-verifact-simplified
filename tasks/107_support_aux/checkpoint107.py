"""Two rolling slots with the auxiliary head in the atomic commit boundary.

The last pointer is replaced only after adapter, head, optimizer, scheduler and
RNG files are complete and hashed.  An interrupted inactive-slot write cannot
replace the previous committed checkpoint.  A complete optimizer checkpoint
must be retained on the instance; an adapter alone is not a training resume.
"""
from pathlib import Path
import random
import sys

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '105_brief_supervision'))
import common105 as c


def assert_head_optimized(optimizer, aux_head):
    if aux_head is None:
        return
    identities = [id(p) for group in optimizer.param_groups for p in group['params']]
    if any(not p.requires_grad or identities.count(id(p)) != 1 for p in aux_head.parameters()):
        raise ValueError('Every trainable auxiliary parameter must occur exactly once in the optimizer')


def save(model, optimizer, scheduler, work, step, consumed, fingerprint, aux_head=None):
    assert_head_optimized(optimizer, aux_head)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    pointer = work / 'resume.json'
    old = c.read(pointer) if pointer.exists() else None
    if old and (old['fingerprint'] != fingerprint or old['slot'] not in {'checkpoint_a', 'checkpoint_b'}):
        raise ValueError('Cannot overwrite a work directory with another configuration/arm')
    slot = 'checkpoint_b' if old and old['slot'] == 'checkpoint_a' else 'checkpoint_a'
    folder = work / slot
    folder.mkdir(exist_ok=True)
    model.save_pretrained(folder, safe_serialization=True)
    head_path = folder / 'aux_head.pt'
    if aux_head is not None:
        temporary = folder / 'aux_head.pt.tmp'
        torch.save(aux_head.state_dict(), temporary)
        temporary.replace(head_path)
    elif head_path.exists():
        head_path.unlink()
    state = dict(optimizer=optimizer.state_dict(), scheduler=scheduler.state_dict(), step=step, consumed=consumed,
                 torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [],
                 python_rng=random.getstate(), numpy_rng=np.random.get_state(), fingerprint=fingerprint,
                 has_aux_head=aux_head is not None, checkpoint_version=107)
    temporary = folder / 'training_state.pt.tmp'
    torch.save(state, temporary)
    temporary.replace(folder / 'training_state.pt')
    files = {p.name: c.sha(p) for p in folder.iterdir()
             if p.is_file() and p.name != 'checkpoint_complete.json' and not p.name.endswith('.tmp')}
    complete = dict(step=step, consumed=consumed, fingerprint=fingerprint, files=files,
                    has_aux_head=aux_head is not None, checkpoint_version=107)
    c.put(folder / 'checkpoint_complete.json', complete)
    c.put(pointer, dict(slot=slot, step=step, consumed=consumed,
                        complete_sha256=c.sha(folder / 'checkpoint_complete.json'), fingerprint=fingerprint))
    return folder


def load(optimizer, scheduler, work, fingerprint, restore_adapter, aux_head=None):
    assert_head_optimized(optimizer, aux_head)
    work = Path(work)
    pointer = c.read(work / 'resume.json')
    if pointer['fingerprint'] != fingerprint:
        raise ValueError('Resume configuration/data/code fingerprint mismatch')
    if pointer['slot'] not in {'checkpoint_a', 'checkpoint_b'}:
        raise ValueError('Unexpected checkpoint path')
    folder = work / pointer['slot']
    if c.sha(folder / 'checkpoint_complete.json') != pointer['complete_sha256']:
        raise ValueError('Checkpoint commit hash mismatch')
    complete = c.read(folder / 'checkpoint_complete.json')
    if (complete['fingerprint'] != fingerprint or complete.get('checkpoint_version') != 107
            or complete.get('has_aux_head') != (aux_head is not None)):
        raise ValueError('Checkpoint arm/configuration mismatch')
    required = {'training_state.pt'} | ({'aux_head.pt'} if aux_head is not None else set())
    if not required.issubset(complete['files']):
        raise ValueError('Incomplete training/head checkpoint')
    for name, expected in complete['files'].items():
        if Path(name).name != name or not (folder / name).is_file() or c.sha(folder / name) != expected:
            raise ValueError('Checkpoint file hash/path mismatch: ' + name)
    state = torch.load(folder / 'training_state.pt', map_location='cpu', weights_only=False)
    if (state['step'] != pointer['step'] or state['consumed'] != pointer['consumed']
            or complete['step'] != pointer['step'] or complete['consumed'] != pointer['consumed']
            or state['fingerprint'] != fingerprint or state.get('has_aux_head') != (aux_head is not None)
            or state.get('checkpoint_version') != 107):
        raise ValueError('Checkpoint state cursor/configuration mismatch')
    restore_adapter(folder)
    if aux_head is not None:
        aux_head.load_state_dict(torch.load(folder / 'aux_head.pt', map_location='cpu', weights_only=True), strict=True)
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    torch.set_rng_state(state['torch_rng'])
    random.setstate(state['python_rng'])
    np.random.set_state(state['numpy_rng'])
    if state['cuda_rng']:
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    return pointer['step'], pointer['consumed'], folder
