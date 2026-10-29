"""Prepared LP-to-LoRA worker; importing this file never loads a model.

Run only after a separately frozen job has been authorized.  Required job keys:
name, model_dir, source107_adapter, selected_head_npz,
selected_head_selection_json, train_path, validation_path, screen_inputs_path,
session_path, max_seq_length, phase_limit_seconds, validation_steps, training.
Paths are absolute or relative to the deployed repository root.  Optional
screen_ids select from a GT-free input file; otherwise every input row is used.
training requires epochs and learning_rate; it accepts total_steps (a ceiling),
gradient_accumulation, head_learning_rate, betas, eps, weight_decay and
gradient_clip.  microbatch must remain1.  Input order is preserved each epoch.
Optional initial_validation_cache and initial_screen_cache paths reuse only
step0 predictions.  Each JSON contains source_adapter_sha256, head_sha256 and
records with id, class_index, verdict, valid and probabilities; validation
records additionally contain GT.  Validation must cover the exact validation
set; a screen cache may cover a subset of requested screen IDs.  These are
FP32-head predictions over existing BF16 features, not inferred probabilities
from text receipts.  Other checkpoints always receive a new forward pass.
head_sha256 identifies the job's selected_head_npz file, before FP32 loading.

The objective is the selected head's (possibly class-weighted) three-class
CE, optionally retaining that same probe's L2 regularization. The source107 LoRA is trainable, using a fresh AdamW, with BF16 backbone
execution and its original adapter parameter precision.  The learned head and
its fixed StandardScaler buffers remain FP32.  checkpoint107's aux_head.pt and
has_aux_head fields are reused ONLY for serialization of this sole classifier;
there is no auxiliary head, auxiliary loss, or language-model loss.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common

STOP = False


def request_stop(*_):
    global STOP
    STOP = True


def path_at_root(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('ab') as stream:
        stream.write((common.canonical(value) + '\n').encode('utf-8'))
        stream.flush()


def make_plan(ids, epochs, accumulation, maximum_steps=None):
    if epochs < 1 or accumulation < 1 or len(set(ids)) != len(ids):
        raise ValueError('Positive epochs/accumulation and unique training IDs required')
    plan = []
    consumed = 0
    for epoch in range(epochs):
        for start in range(0, len(ids), accumulation):
            batch_ids = ids[start:start + accumulation]
            consumed += len(batch_ids)
            plan.append(dict(step=len(plan) + 1, epoch=epoch + 1, ids=batch_ids,
                             divisor=len(batch_ids), consumed=consumed))
    if maximum_steps is not None:
        if not 1 <= maximum_steps <= len(plan):
            raise ValueError('total_steps must be within the configured epoch plan')
        plan = plan[:maximum_steps]
    return plan


def point(truth, prediction):
    n = len(truth)
    if not n or len(prediction) != n:
        raise ValueError('Nonempty aligned validation labels required')
    matrix = [[sum(a == i and b == j for a, b in zip(truth, prediction))
               for j in range(3)] for i in range(3)]
    actual = [sum(row) for row in matrix]
    predicted = [sum(matrix[i][j] for i in range(3)) for j in range(3)]
    correct = sum(matrix[i][i] for i in range(3))
    denominator = math.sqrt((n*n - sum(v*v for v in actual)) *
                            (n*n - sum(v*v for v in predicted)))
    return dict(N=n, correct=correct, PA=correct/n,
                MCC=(correct*n - sum(a*b for a, b in zip(actual, predicted))) /
                    denominator if denominator else 0.0,
                false_S=matrix[1][0] + matrix[2][0], confusion=matrix,
                recall=[matrix[i][i]/actual[i] if actual[i] else None for i in range(3)])


def load_initial_cache(path, source_sha, head_sha, labels, expected_ids,
                       expected_gt=None, allow_subset=False):
    """Validate source and row association without replaying the backbone."""
    payload = common.read(path)
    if (payload.get('source_adapter_sha256') != source_sha or
            payload.get('head_sha256') != head_sha):
        raise ValueError('Initial cache differs from the source107 adapter or FP32 head')
    rows = payload.get('records')
    if not isinstance(rows, list):
        raise ValueError('Initial cache requires a records list')
    result = {}
    wanted = set(expected_ids)
    for row in rows:
        identifier = row['id']
        if identifier in result or identifier not in wanted:
            raise ValueError('Duplicate or unexpected initial-cache ID: ' + identifier)
        index = row.get('class_index')
        if type(index) is not int or not 0 <= index < len(labels):
            raise ValueError('Initial cache requires a valid original class index')
        if row.get('valid') is not True or row.get('verdict') != labels[index]:
            raise ValueError('Initial-cache label/index association differs')
        if expected_gt is not None:
            if row.get('GT') != expected_gt[identifier]:
                raise ValueError('Initial-validation cache GT mismatch: ' + identifier)
        elif 'GT' in row:
            raise ValueError('Initial screen cache must be GT-free')
        probabilities = row.get('probabilities')
        if probabilities is not None:
            if (not isinstance(probabilities, dict) or set(probabilities) != set(labels) or
                    not all(isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1
                            for p in probabilities.values()) or
                    abs(sum(probabilities.values())-1) > 1e-4):
                raise ValueError('Invalid initial-cache class probabilities')
            if probabilities[labels[index]] < max(probabilities.values()):
                raise ValueError('Initial-cache probabilities and class index differ')
        record = dict(id=identifier, class_index=index, verdict=labels[index], valid=True,
                      content=common.canonical({'verdict': labels[index]}),
                      probabilities=probabilities, probabilities_calibrated=False,
                      probability_scope='learned_three_class_head',
                      prediction_origin='initial_feature_cache')
        if expected_gt is not None:
            record['GT'] = expected_gt[identifier]
        result[identifier] = record
    if not allow_subset and set(result) != wanted:
        raise ValueError('Initial-validation cache must cover the exact validation IDs')
    return result


def run(job, job_path, out):
    global STOP
    STOP = False
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    session_path = path_at_root(job['session_path'])
    session = common.read(session_path)
    started = time.time()
    reserve = float(job.get('save_reserve_seconds', 180))
    limits = [session['start_epoch'] + session['duration_seconds'],
              started + float(job['phase_limit_seconds'])]
    if session.get('GPU_cap_CNY') is not None:
        limits.append(session['start_epoch'] + 3600*session['GPU_cap_CNY']/session['hourly_CNY'])
    hard_end = min(limits)
    deadline = hard_end - reserve

    def budget(seconds=0):
        if STOP or time.time() + seconds >= deadline:
            raise TimeoutError('LPFT phase/night boundary; preserve checkpoint, do not shut down')

    stage = 'initializing'
    total_steps = 0
    step = consumed = 0
    model = head = optimizer = scheduler = None
    partial_step = update_in_progress = False
    boundary_rng = None
    fingerprint = None
    work = out / 'train'
    work.mkdir(parents=True, exist_ok=True)

    def progress(value, completed, total, remaining=None):
        nonlocal stage
        stage = value
        common.put(out / 'progress.json', dict(stage=value, completed=completed, total=total,
                   remaining_seconds=remaining, epoch=time.time(), no_shutdown=True))

    try:
        budget(60)
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          HF_HUB_DISABLE_TELEMETRY='1')
        from unsloth import FastLanguageModel as Fast
        import numpy as np
        import torch
        from transformers import AutoTokenizer
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        sys.path.insert(0, str(ROOT / 'tasks/107_support_aux'))
        import checkpoint107 as checkpoint
        import learned_head117 as method

        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('This worker requires BF16 CUDA; no quantized or CPU fallback')
        tr = job['training']
        if int(tr.get('microbatch', 1)) != 1:
            raise ValueError('The prepared training contract is full-input microbatch1')
        epochs = int(tr['epochs'])
        accumulation = int(tr.get('gradient_accumulation', 8))
        seed = int(job.get('seed', 117027))
        lr = float(tr['learning_rate'])
        head_lr = float(tr.get('head_learning_rate', lr))
        clip = float(tr.get('gradient_clip', 1.0))
        if not all(math.isfinite(v) and v > 0 for v in (lr, head_lr, clip)):
            raise ValueError('Positive finite learning rates and gradient clip required')
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

        train_path = path_at_root(job['train_path'])
        validation_path = path_at_root(job['validation_path'])
        screen_path = path_at_root(job['screen_inputs_path'])
        train_rows = common.rows(train_path)
        validation = common.rows(validation_path)
        labels = tuple(method.LABELS)
        for role, rows in (('train', train_rows), ('validation', validation)):
            if not rows or len({r['id'] for r in rows}) != len(rows):
                raise ValueError(role + ' requires nonempty unique IDs')
            if {r['GT'] for r in rows} != set(labels):
                raise ValueError(role + ' requires all three original GT classes')
            if any(not str(r['sid']) for r in rows):
                raise ValueError('Patient metadata required to check isolation')
        if ({r['id'] for r in train_rows} & {r['id'] for r in validation} or
                {str(r['sid']) for r in train_rows} & {str(r['sid']) for r in validation}):
            raise ValueError('Train/validation ID or patient overlap')
        screens = common.rows(screen_path)
        if len({r['id'] for r in screens}) != len(screens):
            raise ValueError('Duplicate screen input IDs')
        forbidden = {'GT', 'human_gt', 'label', 'sid', 'panel', 'verdict', 'answer', 'answer_text'}
        if any(forbidden & set(r) for r in screens):
            raise ValueError('Screen model-input file must be GT-free')
        screen_by_id = {r['id']: r for r in screens}
        screen_ids = list(job.get('screen_ids', screen_by_id))
        if not screen_ids or len(set(screen_ids)) != len(screen_ids):
            raise ValueError('Nonempty unique screen IDs required')
        if (not set(screen_ids) <= set(screen_by_id) or set(screen_ids) &
                ({r['id'] for r in train_rows} | {r['id'] for r in validation})):
            raise ValueError('Missing screen input or screen/training ID overlap')
        plan = make_plan([r['id'] for r in train_rows], epochs, accumulation,
                         int(tr['total_steps']) if tr.get('total_steps') is not None else None)
        total_steps = len(plan)
        validation_steps = {int(v) for v in job['validation_steps']}
        if (not {0, total_steps} <= validation_steps or
                any(v < 0 or v > total_steps for v in validation_steps)):
            raise ValueError('validation_steps must include0 and the actual final step')
        common.put(out / 'plan.json', plan)

        source = path_at_root(job['source107_adapter'])
        source_file = source / 'adapter_model.safetensors'
        source_config = common.read(source / 'adapter_config.json')
        source_sha = common.sha(source_file)
        if job.get('source_adapter_sha256') and source_sha != job['source_adapter_sha256']:
            raise ValueError('Source107 adapter mismatch')
        head_path = path_at_root(job['selected_head_npz'])
        selection_path = path_at_root(job['selected_head_selection_json'])
        selection = common.read(selection_path)
        head = method.LearnedHead.from_npz(head_path, device='cuda')
        if head.representation != 'verdict_prefix':
            raise ValueError('This LPFT candidate requires the selected verdict-prefix head')
        selected = selection['representations'][head.representation]
        policy = selected['class_weight']
        counts = Counter(r['GT'] for r in train_rows)
        if policy is None:
            weight_values = [1.0] * 3
        elif policy == 'balanced':
            weight_values = [len(train_rows)/(3*counts[label]) for label in labels]
        elif isinstance(policy, dict) and set(policy) == set(labels):
            weight_values = [float(policy[label]) for label in labels]
        else:
            raise ValueError('Unsupported selected class_weight; do not infer another policy')
        class_weights = torch.tensor(weight_values, dtype=torch.float32, device='cuda')
        if not bool(torch.isfinite(class_weights).all() and (class_weights > 0).all()):
            raise ValueError('Selected class weights must be positive and finite')
        # Preserve the probe's own L2 objective when requested; sklearn's
        # sum-loss + ||W||²/(2C) becomes this coefficient for mean CE.
        head_l2 = (1.0 / (float(selected['C']) * sum(counts[g] * w for g, w in zip(labels, weight_values)))
                   if job.get('retain_probe_l2', False) else 0.0)

        fingerprint = dict(job=common.digest(common.canonical(job)),
                           train=common.sha(train_path), validation=common.sha(validation_path),
                           screen_inputs=common.sha(screen_path), source107=source_sha,
                           selected_head=common.sha(head_path), selection=common.sha(selection_path),
                           worker=common.sha(Path(__file__)),
                           helper=common.sha(Path(method.__file__)), class_weights=weight_values)
        for key in ('initial_validation_cache', 'initial_screen_cache'):
            if job.get(key):
                fingerprint[key] = common.sha(path_at_root(job[key]))
        model_dir = path_at_root(job['model_dir'])
        if (model_dir / 'adapter_config.json').exists():
            raise ValueError('model_dir must contain the common original9B base')
        maximum_length = int(job['max_seq_length'])
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        rows_by_id = {r['id']: r for r in train_rows + validation}
        all_inputs = list(rows_by_id.values()) + [screen_by_id[i] for i in screen_ids]
        encoded = {}
        for row in all_inputs:
            ids = method.prompt_ids(tokenizer, row)
            if len(ids) > maximum_length:
                raise ValueError('Full input exceeds configured context: ' + row['id'])
            expected = row.get('expected_prompt_sha256') or row.get('input_token_sha256')
            if expected and common.digest(common.canonical(ids[:-len(method.PREFIX_IDS)])) != expected:
                raise ValueError('Original prompt differs: ' + row['id'])
            encoded[row['id']] = ids
        budget(60)
        progress('loading', 0, total_steps)
        model, _ = Fast.from_pretrained(
            model_name=str(model_dir), max_seq_length=maximum_length, dtype=torch.bfloat16,
            load_in_4bit=False, load_in_8bit=False, full_finetuning=False,
            device_map={'': 0}, trust_remote_code=False, local_files_only=True)
        model = Fast.get_peft_model(
            model, r=source_config['r'], lora_alpha=source_config['lora_alpha'],
            lora_dropout=source_config.get('lora_dropout', 0.0), bias=source_config.get('bias', 'none'),
            target_modules=source_config['target_modules'], use_gradient_checkpointing=True,
            random_state=seed, use_rslora=source_config.get('use_rslora', False),
            finetune_vision_layers=False, finetune_language_layers=True)

        def restore_adapter(folder):
            incompatible = set_peft_model_state_dict(
                model, load_file(str(Path(folder) / 'adapter_model.safetensors')))
            missing = getattr(incompatible, 'missing_keys', ())
            if any('lora_' in key for key in missing) or getattr(incompatible, 'unexpected_keys', ()):
                raise ValueError('Adapter keys do not match the original LoRA modules')

        restore_adapter(source)
        Fast.for_training(model)
        named = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
        if not named or any('lora_' not in name or 'visual' in name or 'vision' in name
                            for name, p in named):
            raise ValueError('Only the original language LoRA may be trainable in the backbone')
        lora_params = [p for name, p in named]
        if sum(p.numel() for p in lora_params) != int(job.get('expected_lora_parameters', 43278336)):
            raise ValueError('LoRA coverage differs from source107')
        if not any(bool(p.detach().count_nonzero()) for name, p in named if 'lora_B' in name):
            raise ValueError('Source107 must have nonzero trained LoRA-B')
        if (getattr(model, 'is_loaded_in_4bit', False) or getattr(model, 'is_loaded_in_8bit', False)
                or any(p.device.type != 'cuda' for p in model.parameters())):
            raise ValueError('No quantization or CPU offload is authorized by this worker')
        head_params = list(head.parameters())
        if any(not p.requires_grad or p.dtype != torch.float32 for p in head_params):
            raise ValueError('All classifier parameters must be trainable FP32')
        all_params = lora_params + head_params
        optimizer = torch.optim.AdamW(
            [{'params': lora_params, 'lr': lr}, {'params': head_params, 'lr': head_lr}],
            betas=tuple(tr.get('betas', (.9, .999))), eps=float(tr.get('eps', 1e-8)),
            weight_decay=float(tr.get('weight_decay', 0.0)))
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda _: 1.0)
        checkpoint.assert_head_optimized(optimizer, head)
        if optimizer.state:
            raise ValueError('New objective requires fresh Adam, not source107 LM moments')
        common.put(out / 'setup.json', dict(
            fingerprint=fingerprint, training_N=len(train_rows), validation_N=len(validation),
            training_patients=len({str(r['sid']) for r in train_rows}),
            validation_patients=len({str(r['sid']) for r in validation}),
            ancestor107_saw_some_validation=True, epochs=epochs, total_steps=total_steps,
            presentations=plan[-1]['consumed'], validation_steps=sorted(validation_steps),
            class_weight_policy=policy, class_weights=dict(zip(labels, weight_values)),
            class_weight_counts=dict(counts), source_LoRA_dtypes=dict(Counter(str(p.dtype) for p in lora_params)),
            fresh_Adam=True, sole_objective='weighted_three_class_CE_with_same_head_L2' if head_l2 else 'weighted_three_class_CE',
            retained_head_L2_coefficient=head_l2,
            head_FP32=True, scaler_buffers_fixed=True,
            aux_head_pt_is_only_serialization_of_the_sole_classifier=True,
            auxiliary_loss=False, language_model_loss=False, no_shutdown=True))
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

        def tensor(ids):
            sequences = [encoded[i] for i in ids]
            width = max(map(len, sequences))
            return dict(input_ids=torch.tensor([[pad]*(width-len(x)) + x for x in sequences], device='cuda'),
                        attention_mask=torch.tensor([[0]*(width-len(x)) + [1]*len(x)
                                                     for x in sequences], device='cuda'))

        def capture_rng():
            return torch.get_rng_state(), torch.cuda.get_rng_state_all(), random.getstate(), np.random.get_state()

        def restore_rng(value):
            torch.set_rng_state(value[0])
            torch.cuda.set_rng_state_all(value[1])
            random.setstate(value[2])
            np.random.set_state(value[3])

        def save_checkpoint():
            return checkpoint.save(model, optimizer, scheduler, work, step, consumed,
                                   fingerprint, aux_head=head)

        if (work / 'resume.json').exists():
            step, consumed, _ = checkpoint.load(optimizer, scheduler, work, fingerprint,
                                                restore_adapter, aux_head=head)
            if not 0 <= step <= total_steps or consumed != (plan[step-1]['consumed'] if step else 0):
                raise ValueError('Resume cursor differs from the fixed training plan')
        else:
            save_checkpoint()
        if [g['lr'] for g in optimizer.param_groups] != [lr, head_lr]:
            raise ValueError('Restored learning rates differ from the configured fixed rates')

        if not (out / 'gpu_gate.json').exists():
            budget(90)
            progress('longest_backward_gate', step, total_steps)
            rng = capture_rng()
            identifier = max((r['id'] for r in train_rows), key=lambda i: len(encoded[i]))
            batch = tensor([identifier])
            # Match the memory of Adam's two moment tensors without advancing it.
            reserve_tensors = [] if optimizer.state else [torch.zeros_like(p) for p in all_params for _ in range(2)]
            optimizer.zero_grad(set_to_none=True)
            torch.cuda.reset_peak_memory_stats()
            began = time.perf_counter()
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss, scores = method.classification_loss(
                    model, head, batch, [rows_by_id[identifier]['GT']], class_weights=class_weights)
                if head_l2:
                    loss = loss + 0.5 * head_l2 * head.linear.weight.square().sum()
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(all_params, clip)
            torch.cuda.synchronize()
            if not bool(torch.isfinite(loss) and torch.isfinite(norm)):
                raise FloatingPointError('Nonfinite full-input gate loss/gradient')
            if (not any(p.grad is not None and bool(p.grad.count_nonzero()) for p in lora_params) or
                    not any(p.grad is not None and bool(p.grad.count_nonzero()) for p in head_params)):
                raise RuntimeError('Both the sole head and source LoRA must receive nonzero gradients')
            free, total = torch.cuda.mem_get_info()
            external = max(0, total-free-torch.cuda.memory_reserved())
            margin = total-external-torch.cuda.max_memory_allocated()
            if margin < int(job.get('minimum_headroom_bytes', 256*1024**2)):
                raise RuntimeError('Longest full-input backward has insufficient memory headroom')
            common.put(out / 'gpu_gate.json', dict(fingerprint=fingerprint, input_tokens=len(encoded[identifier]),
                       seconds=time.perf_counter()-began, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                       physical_headroom_bytes=margin, microbatch=1, LoRA_gradient=True, head_gradient=True,
                       class_weight_applied=True, optimizer_updates=0, no_input_truncation=True))
            del batch, reserve_tensors, loss, scores
            optimizer.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
            restore_rng(rng)
        elif common.read(out / 'gpu_gate.json')['fingerprint'] != fingerprint:
            raise ValueError('Gate belongs to another job')

        def predict(ids):
            batch = tensor(ids)
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                scores = method.logits(model, head, batch)
            values = scores.float().cpu()
            records = []
            for row_scores in values:
                if not bool(torch.isfinite(row_scores).all()):
                    records.append(dict(verdict=None, valid=False, error='nonfinite_logits', probabilities=None))
                    continue
                index = int(row_scores.argmax())
                probability = row_scores.softmax(-1).tolist()
                records.append(dict(verdict=labels[index], class_index=index, valid=True,
                                    content=common.canonical({'verdict': labels[index]}),
                                    probabilities=dict(zip(labels, probability)),
                                    probabilities_calibrated=False,
                                    probability_scope='learned_three_class_head'))
            return records

        def validate():
            path = out / 'validation' / f'step-{step:06d}.json'
            progress('internal_validation', step, total_steps)
            if path.exists():
                result = common.read(path)
                if result['fingerprint'] != fingerprint or result['step'] != step:
                    raise ValueError('Validation cache differs from this checkpoint')
            elif step == 0 and job.get('initial_validation_cache'):
                cached = load_initial_cache(
                    path_at_root(job['initial_validation_cache']), source_sha,
                    fingerprint['selected_head'], labels, [r['id'] for r in validation],
                    expected_gt={r['id']: r['GT'] for r in validation})
                records = [cached[r['id']] for r in validation]
                stats = point([labels.index(r['GT']) for r in records],
                              [r['class_index'] for r in records])
                result = dict(step=0, fingerprint=fingerprint, stats=stats, records=records,
                              initial_cache_used=True, source_adapter_sha256=source_sha,
                              head_sha256=fingerprint['selected_head'])
                common.put(path, result)
            else:
                records = []
                order = sorted(validation, key=lambda r: (len(encoded[r['id']]), r['id']))
                batch_size = int(job.get('validation_batch_size', 2))
                if batch_size < 1:
                    raise ValueError('Positive validation batch size required')
                model.eval()
                head.eval()
                try:
                    for start in range(0, len(order), batch_size):
                        budget(20)
                        part = order[start:start+batch_size]
                        predictions = predict([r['id'] for r in part])
                        if any(not p['valid'] for p in predictions):
                            raise FloatingPointError('Nonfinite internal-validation logits')
                        records.extend(dict(id=r['id'], GT=r['GT'], **p) for r, p in zip(part, predictions))
                finally:
                    model.train()
                    head.train()
                stats = point([labels.index(r['GT']) for r in records], [r['class_index'] for r in records])
                result = dict(step=step, fingerprint=fingerprint, stats=stats, records=records)
                common.put(path, result)
            best_path = out / 'best.json'
            previous = common.read(best_path) if best_path.exists() else None
            if previous and previous['fingerprint'] != fingerprint:
                raise ValueError('Best checkpoint belongs to another job')
            rank = lambda stats: (stats['MCC'], stats['PA'], -stats['false_S'])
            if previous is None or rank(result['stats']) > rank(previous['stats']):
                pointer = common.read(work / 'resume.json')
                if pointer['step'] != step:
                    raise ValueError('Validation and saved checkpoint step differ')
                destination = out / 'selection' / f'step-{step:06d}-{time.time_ns()}'
                destination.parent.mkdir(exist_ok=True)
                shutil.copytree(work / pointer['slot'], destination)
                common.put(best_path, dict(step=step, checkpoint=str(destination), fingerprint=fingerprint,
                           stats=result['stats'], selection='internal_validation_MCC_PA_fewer_falseS',
                           aux_head_pt_is_sole_classifier=True))

        if step in validation_steps:
            validate()
        training_start = time.perf_counter()
        start_step = step
        for entry in plan[step:]:
            budget(45)
            progress('training', step, total_steps)
            optimizer.zero_grad(set_to_none=True)
            boundary_rng = capture_rng()
            partial_step = True
            began = time.perf_counter()
            losses = []
            tokens = 0
            for identifier in entry['ids']:
                budget(15)
                batch = tensor([identifier])
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    loss, scores = method.classification_loss(
                        model, head, batch, [rows_by_id[identifier]['GT']], class_weights=class_weights)
                    if head_l2:
                        loss = loss + 0.5 * head_l2 * head.linear.weight.square().sum()
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError('Nonfinite training loss')
                (loss / entry['divisor']).backward()
                losses.append(float(loss.detach()))
                tokens += len(encoded[identifier])
                del batch, loss, scores
            norm = torch.nn.utils.clip_grad_norm_(all_params, clip)
            if not bool(torch.isfinite(norm)):
                raise FloatingPointError('Nonfinite training gradient')
            update_in_progress = True
            optimizer.step()
            scheduler.step()
            torch.cuda.synchronize()
            step, consumed = entry['step'], entry['consumed']
            update_in_progress = partial_step = False
            append(out / 'steps.jsonl', dict(step=step, epoch=entry['epoch'], consumed=consumed,
                   divisor=entry['divisor'], mean_loss=sum(losses)/len(losses), tokens=tokens,
                   learning_rates=[g['lr'] for g in optimizer.param_groups],
                   seconds=time.perf_counter()-began))
            if step % 16 == 0 or step in validation_steps or step == total_steps:
                save_checkpoint()
            if step in validation_steps:
                validate()
            remaining = ((time.perf_counter()-training_start)/max(1, step-start_step) *
                         (total_steps-step))
            progress('training', step, total_steps, remaining)
        if (step, consumed) != (total_steps, plan[-1]['consumed']):
            raise ValueError('Training did not reach the configured final cursor')
        best = common.read(out / 'best.json')
        chosen = Path(best['checkpoint'])
        complete = common.read(chosen / 'checkpoint_complete.json')
        if complete['fingerprint'] != fingerprint or complete['step'] != best['step']:
            raise ValueError('Selected classifier/LoRA checkpoint mismatch')
        # The rolling checkpoint already contains the final optimizer state.
        # Drop it before changing weights to the selected (possibly earlier)
        # checkpoint, so an evaluation/save failure cannot pair old weights
        # with the final optimizer under a misleading resume cursor.
        optimizer.zero_grad(set_to_none=True)
        optimizer = scheduler = None
        torch.cuda.empty_cache()
        restore_adapter(chosen)
        head.load_state_dict(torch.load(chosen / 'aux_head.pt', map_location='cpu', weights_only=True), strict=True)
        head.save_npz(out / 'selected_head.npz')
        common.put(out / 'training_done.json', dict(steps=step, consumed=consumed,
                   selected_step=best['step'], selected_checkpoint=str(chosen),
                   selected_adapter_sha256=complete['files']['adapter_model.safetensors'],
                   selected_head_sha256=complete['files']['aux_head.pt'], fingerprint=fingerprint,
                   selection_only_internal_validation=True, sole_classifier_head=True,
                   auxiliary_loss=False, no_shutdown=True, epoch=time.time()))
        Fast.for_inference(model)
        model.eval()
        head.eval()
        order = sorted(screen_ids, key=lambda i: (len(encoded[i]), i))
        batch_size = int(job.get('screen_batch_size', 2))
        if batch_size < 1:
            raise ValueError('Positive screen batch size required')
        predictions_dir = out / 'predictions'
        predictions_dir.mkdir(exist_ok=True)
        received = {}
        for identifier in order:
            path = predictions_dir / f'{identifier}.json'
            if path.exists():
                value = common.read(path)
                if (value['fingerprint'] != fingerprint or value['selected_step'] != best['step'] or
                        value['id'] != identifier):
                    raise ValueError('Existing first screen prediction belongs to another checkpoint')
                received[identifier] = value
        if best['step'] == 0 and job.get('initial_screen_cache'):
            cached = load_initial_cache(
                path_at_root(job['initial_screen_cache']), source_sha,
                fingerprint['selected_head'], labels, screen_ids, allow_subset=True)
            for identifier, value in cached.items():
                if identifier in received:
                    continue
                record = dict(value, fingerprint=fingerprint, selected_step=0,
                              input_tokens=len(encoded[identifier]),
                              internal_prompt_sha256=common.digest(common.canonical(encoded[identifier])),
                              source_prompt_sha256_104=screen_by_id[identifier].get('expected_prompt_sha256'),
                              source_adapter_sha256=source_sha,
                              head_sha256=fingerprint['selected_head'],
                              no_ground_truth_in_model_input=True)
                common.put(predictions_dir / f'{identifier}.json', record)
                received[identifier] = record
        progress('development_screen', len(received), len(order))
        for start in range(0, len(order), batch_size):
            ids = [i for i in order[start:start+batch_size] if i not in received]
            if not ids:
                continue
            budget(20)
            for identifier, value in zip(ids, predict(ids)):
                record = dict(id=identifier, **value, fingerprint=fingerprint,
                              selected_step=best['step'], input_tokens=len(encoded[identifier]),
                              internal_prompt_sha256=common.digest(common.canonical(encoded[identifier])),
                              source_prompt_sha256_104=screen_by_id[identifier].get('expected_prompt_sha256'),
                              no_ground_truth_in_model_input=True)
                common.put(predictions_dir / f'{identifier}.json', record)
                received[identifier] = record
            progress('development_screen', len(received), len(order))
        common.putl(out / 'screen_predictions.jsonl', [received[i] for i in screen_ids])
        initial_screen_reused = sum(p.get('prediction_origin') == 'initial_feature_cache'
                                    for p in received.values())
        common.put(out / 'complete.json', dict(N=len(received), valid=sum(p['valid'] for p in received.values()),
                   steps=step, consumed=consumed, selected_step=best['step'],
                   initial_screen_reused=initial_screen_reused,
                   checkpoint=str(chosen), fingerprint=fingerprint, no_shutdown=True, epoch=time.time()))
        progress('complete', len(received), len(order), 0)
    except BaseException as error:
        emergency_error = None
        # A partially applied optimizer update is never advertised as resumable.
        # Otherwise discard partial gradients/RNG consumption and save the last
        # completed update, even if it was between regular16-step checkpoints.
        if optimizer is not None and fingerprint is not None and not update_in_progress:
            try:
                if partial_step and boundary_rng is not None:
                    restore_rng(boundary_rng)
                optimizer.zero_grad(set_to_none=True)
                save_checkpoint()
            except BaseException as save_error:
                emergency_error = repr(save_error)
        pointer = common.read(work / 'resume.json') if (work / 'resume.json').exists() else None
        common.put(out / 'failure.json', dict(stage=stage, error_type=type(error).__name__, error=str(error),
                   latest_completed_step=step, saved_step=pointer['step'] if pointer else None,
                   partial_optimizer_update_not_saved=update_in_progress,
                   emergency_checkpoint_error=emergency_error, no_input_truncation=True,
                   no_shutdown=True, epoch=time.time()))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = ROOT / 'data' / job_path
    job = common.read(job_path)
    name = job['name']
    if not isinstance(name, str) or not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in name):
        raise ValueError('Use a simple lowercase job name')
    out = path_at_root(job['output_dir']) if job.get('output_dir') else ROOT / 'results' / name
    out.mkdir(parents=True, exist_ok=True)
    run(job, job_path, out)


if __name__ == '__main__':
    main()
