"""Disposable same-next-step diagnosis; never grants permission to train.

Restore the already saved real gate step1, compare repeated disk restores and
an independent CPU-cloned in-memory restore. Report exact hashes AND numerical
differences. No threshold is relaxed and no formal optimizer state is written.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import math
from pathlib import Path
import platform
import random
import time

import common107 as c
import worker107 as w


def cpu_clone(value, torch):
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_clone(part, torch) for key, part in value.items()}
    if isinstance(value, list):
        return [cpu_clone(part, torch) for part in value]
    if isinstance(value, tuple):
        return tuple(cpu_clone(part, torch) for part in value)
    return deepcopy(value)


def flatten_tensors(value, torch, prefix='state'):
    if torch.is_tensor(value):
        return {prefix: value}
    result = {}
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            result.update(flatten_tensors(value[key], torch, prefix + '/' + str(key)))
    elif isinstance(value, (list, tuple)):
        for index, part in enumerate(value):
            result.update(flatten_tensors(part, torch, prefix + '/' + str(index)))
    return result


def tensor_difference(left, right, torch):
    names = sorted(set(left) | set(right))
    rows = []
    squared = reference_squared = 0.
    changed = elements = 0
    max_abs = 0.
    finite = True
    for name in names:
        if name not in left or name not in right:
            rows.append(dict(name=name, missing_left=name not in left, missing_right=name not in right))
            finite = False
            continue
        a, b = left[name], right[name]
        if a.shape != b.shape or a.dtype != b.dtype:
            rows.append(dict(name=name, shape_or_dtype_mismatch=True))
            finite = False
            continue
        ok = bool(torch.isfinite(a).all() and torch.isfinite(b).all())
        finite = finite and ok
        elements += a.numel()
        count = int((a != b).sum())
        changed += count
        delta = b.to(torch.float64) - a.to(torch.float64)
        local_sq = float(delta.square().sum())
        squared += local_sq
        reference_squared += float(a.to(torch.float64).square().sum())
        local_max = float(delta.abs().max()) if delta.numel() else 0.
        max_abs = max(max_abs, local_max)
        if count or not ok:
            rows.append(dict(name=name, different_elements=count, elements=a.numel(),
                             max_abs=local_max if math.isfinite(local_max) else None,
                             l2=math.sqrt(local_sq) if math.isfinite(local_sq) else None, finite=ok))
    return dict(tensor_count=len(names), elements=elements, different_elements=changed, finite=finite,
                exactly_equal=not rows, max_abs=max_abs if math.isfinite(max_abs) else None,
                l2=math.sqrt(squared) if math.isfinite(squared) else None,
                relative_l2=math.sqrt(squared / reference_squared) if reference_squared and math.isfinite(squared) else None,
                largest_tensor_differences=sorted(rows, key=lambda row: row.get('max_abs') or 0., reverse=True)[:12])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'work', 'model-dir', 'ledger', 'session'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-rented-gpu', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not args.execute_rented_gpu or platform.system() != 'Linux':
        raise PermissionError('Only the handed-off Linux rented GPU may run this diagnostic')
    w.verify_bundle(args.bundle)
    w.verify_authorization(args.bundle, args.session)
    w.require_budget(args.ledger, 180)
    args.mode = 'resume_diagnostic'
    args.arm = 'support_aux'
    config = c.read(args.bundle / 'frozen/config.json')
    model, tokenizer, Fast, torch = w.load(args, config)
    from loss107 import backbone_loss
    import checkpoint107 as ckpt
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    import numpy as np

    scratch = args.work / 'resume_diagnostic'
    scratch.mkdir(exist_ok=True)
    model, _ = w.adapt(model, Fast, config, scratch)
    head = w.make_head(model, config, 'support_aux')
    parameters, optimizer, scheduler = w.optimizer_for(model, head, config, torch)
    named = dict((name, parameter) for name, parameter in model.named_parameters() if parameter.requires_grad)
    named.update(('aux.' + name, parameter) for name, parameter in head.named_parameters())

    def assert_binding():
        current = dict((name, parameter) for name, parameter in model.named_parameters() if parameter.requires_grad)
        current.update(('aux.' + name, parameter) for name, parameter in head.named_parameters())
        optimized = [parameter for group in optimizer.param_groups for parameter in group['params']]
        identities = [id(parameter) for parameter in optimized]
        if (set(current) != set(named) or any(current[name] is not parameter for name, parameter in named.items())
                or len(identities) != len(set(identities)) or set(identities) != {id(parameter) for parameter in current.values()}):
            raise RuntimeError('PEFT/head parameter identities no longer match the optimizer binding')

    assert_binding()
    checkpoint = args.work / 'gate/restore_probe'
    pointer = c.read(checkpoint / 'resume.json')
    if pointer['step'] != 1 or pointer['consumed'] != 1:
        raise ValueError('Diagnostic only accepts the disposable gate step1/consumed1')
    fingerprint = pointer['fingerprint']
    rows = {row['id']: row for row in c.rows(args.bundle / 'data/train/label_only.jsonl')}
    lengths = [row for row in c.rows(args.bundle / 'frozen/train_token_lengths.jsonl') if row['arm'] == 'label_only']
    shortest = min(lengths, key=lambda row: row['total_tokens'])
    batch, encoded = w.tensor_batch(tokenizer, rows[shortest['id']], torch)
    model.train()

    def restore_disk():
        optimizer.zero_grad(set_to_none=True)
        def restore_adapter(folder):
            set_peft_model_state_dict(model, load_file(str(folder / 'adapter_model.safetensors')))
        step, consumed, _ = ckpt.load(optimizer, scheduler, checkpoint, fingerprint, restore_adapter, aux_head=head)
        assert_binding()
        if (step, consumed) != (1, 1):
            raise ValueError('Unexpected restore cursor')

    def snapshot():
        return dict(params={name: parameter.detach().cpu().clone() for name, parameter in named.items()},
                    optimizer=cpu_clone(optimizer.state_dict(), torch), scheduler=deepcopy(scheduler.state_dict()),
                    torch_rng=torch.get_rng_state().clone(), cuda_rng=[item.clone() for item in torch.cuda.get_rng_state_all()],
                    python_rng=deepcopy(random.getstate()), numpy_rng=deepcopy(np.random.get_state()))

    def restore_memory(state):
        optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            for name, parameter in named.items():
                parameter.copy_(state['params'][name])
        # A fresh deep CPU copy prevents load_state_dict/step from aliasing the
        # saved in-memory baseline, including CPU Adam step counters.
        optimizer.load_state_dict(cpu_clone(state['optimizer'], torch))
        scheduler.load_state_dict(deepcopy(state['scheduler']))
        torch.set_rng_state(state['torch_rng'].clone())
        torch.cuda.set_rng_state_all([item.clone() for item in state['cuda_rng']])
        random.setstate(deepcopy(state['python_rng']))
        np.random.set_state(deepcopy(state['numpy_rng']))
        assert_binding()

    def hashes():
        metadata = {name: dict(device=str(value.device), dtype=str(value.dtype), shape=list(value.shape),
                               stride=list(value.stride()), layout=str(value.layout))
                    for name, value in flatten_tensors(optimizer.state_dict(), torch).items()}
        return dict(parameters=w.parameter_digest(list(named.items())),
                    optimizer=w.state_digest(optimizer.state_dict()), scheduler=w.state_digest(scheduler.state_dict()),
                    RNG=w.rng_digest(torch), buffers=w.parameter_digest(list(model.named_buffers())),
                    optimizer_layout_device_stride=c.digest(c.canonical(metadata)))

    def run_next(label):
        w.require_budget(args.ledger, 120)
        optimizer.zero_grad(set_to_none=True)
        before = hashes()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        begin = time.perf_counter()
        with torch.autocast('cuda', dtype=torch.bfloat16):
            loss, info = backbone_loss(model, batch, aux_head=head, chunk_tokens=config['training']['head_chunk_tokens'])
        loss_value = float(loss.detach())
        loss.backward()
        raw_gradients = {name: parameter.grad.detach().cpu().clone() for name, parameter in named.items() if parameter.grad is not None}
        norm = torch.nn.utils.clip_grad_norm_(parameters, config['training']['gradient_clip'])
        clipped_gradients = {name: parameter.grad.detach().cpu().clone() for name, parameter in named.items() if parameter.grad is not None}
        optimizer.step()
        scheduler.step()
        torch.cuda.synchronize()
        after = hashes()
        output = dict(label=label, before=before, after=after, loss=loss_value,
                      main_loss=info['main_loss'], aux_loss=info['aux_loss'], grad_norm=float(norm),
                      finite_loss=math.isfinite(loss_value), seconds=time.perf_counter() - begin,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      raw_gradient_sha256=w.parameter_digest(list(raw_gradients.items())),
                      clipped_gradient_sha256=w.parameter_digest(list(clipped_gradients.items())),
                      gradients_with_values=len(raw_gradients))
        state = snapshot()
        optimizer.zero_grad(set_to_none=True)
        del loss
        return output, state, raw_gradients, clipped_gradients

    restore_disk()
    baseline = snapshot()
    baseline_hashes = hashes()
    results = []
    comparisons = []
    reference = None
    report_path = args.report or args.work / 'resume_diagnostic107.json'
    report = dict(task=107, scope='disposable_gate_checkpoint_repeated_same_next_step_only',
                  original_checkpoint_pointer_sha256=c.sha(checkpoint / 'resume.json'),
                  original_checkpoint_cursor=dict(step=1, consumed=1), batch_total_tokens=len(encoded['input_ids']),
                  source_training_row_id_sha256=c.digest(shortest['id']),
                  bundle_sha256=c.sha(args.bundle / 'manifest.json'), baseline_hashes=baseline_hashes,
                  official_gate_modified=False, formal_training_started=False, tolerances_relaxed=False,
                  parameter_identity_optimizer_binding_checked_before_after_every_load=True,
                  runs=results, comparisons=comparisons)
    c.put(report_path, report)
    for label in ('disk_first', 'disk_repeat', 'memory_independent_clone'):
        if label == 'memory_independent_clone':
            restore_memory(baseline)
        else:
            restore_disk()
        item = run_next(label)
        results.append(item[0])
        item[0]['initial_state_exactly_matches_disk_baseline'] = all(item[0]['before'][name] == baseline_hashes[name]
                                                                     for name in ('parameters', 'optimizer', 'scheduler', 'RNG'))
        if reference is None:
            reference = item
        else:
            first, first_state, first_raw, first_clipped = reference
            current, current_state, current_raw, current_clipped = item
            parameter_comparisons = {}
            for group in ('LoRA', 'aux_head'):
                select = lambda values: {name: value for name, value in values.items() if name.startswith('aux.') == (group == 'aux_head')}
                parameter_comparisons[group] = tensor_difference(select(first_state['params']), select(current_state['params']), torch)
            comparisons.append(dict(reference=first['label'], candidate=label,
                                    loss_abs_difference=abs(first['loss'] - current['loss']),
                                    main_loss_abs_difference=abs(first['main_loss'] - current['main_loss']),
                                    aux_loss_abs_difference=abs(first['aux_loss'] - current['aux_loss']),
                                    raw_gradients=tensor_difference(first_raw, current_raw, torch),
                                    clipped_gradients=tensor_difference(first_clipped, current_clipped, torch),
                                    parameters=parameter_comparisons,
                                    optimizer_tensors=tensor_difference(flatten_tensors(first_state['optimizer'], torch),
                                                                      flatten_tensors(current_state['optimizer'], torch), torch),
                                    exact_after_hashes={name: first['after'][name] == current['after'][name]
                                                        for name in first['after']}))
        c.put(report_path, report)
        if item is not reference:
            del item
    report['diagnostic_complete'] = True
    report['all_initial_states_exact'] = all(item['initial_state_exactly_matches_disk_baseline'] for item in results)
    report['repeated_disk_next_steps_exact'] = all(all(row['exact_after_hashes'].values()) and row['raw_gradients']['exactly_equal']
                                                for row in comparisons if row['candidate'].startswith('disk_'))
    report['in_memory_vs_disk_next_step_exact'] = next(row for row in comparisons if row['candidate'] == 'memory_independent_clone')['exact_after_hashes']
    report['interpretation_limit'] = ('Repeated disk differences from exactly identical initial state indicate runtime computation or unrecorded mutable state; '
                                      'an in-memory branch with the same scale of differences does not identify checkpoint serialization as the cause. '
                                      'These measurements do not grant a PASS or authorize formal training.')
    c.put(report_path, report)
    print(c.canonical(dict(report=str(report_path), diagnostic_complete=True,
                           all_initial_states_exact=report['all_initial_states_exact'],
                           repeated_disk_next_steps_exact=report['repeated_disk_next_steps_exact'], formal_training_started=False)))


if __name__ == '__main__':
    main()
