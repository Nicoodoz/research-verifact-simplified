"""Prepare or explicitly run missing120 predictions from its fixed final adapter.

Preparation and self-test are CPU-only. Only the explicit ``run`` command loads
the original9B. No training, GT routing, receipt retry, truncation or shutdown.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/120_full_pool_sft'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
from parse105 import parse
from analyze120 import collect

STOP = False


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT/path


def remaining_ids(target, prior):
    if len(target) != len(set(target)):
        raise ValueError('Duplicate target IDs')
    ids = [r['id'] for r in prior]
    if len(ids) != len(set(ids)) or not set(ids) <= set(target):
        raise ValueError('Prior receipts are duplicate or outside the requested cohort')
    return [i for i in target if i not in set(ids)]


def session_deadline(session):
    for key in ('start_epoch', 'duration_seconds', 'GPU_cap_CNY', 'hourly_CNY'):
        if not isinstance(session.get(key), (int, float)) or session[key] <= 0:
            raise ValueError('Missing active session timing/budget: '+key)
    if session.get('no_shutdown') is not True:
        raise ValueError('The current session must preserve user no-shutdown policy')
    return min(session['start_epoch']+session['duration_seconds'],
               session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'])


def prepare(a):
    original = common.read(a.training_job)
    done_file = a.training_result/'training_done.json' if a.training_result.is_dir() else a.training_result
    done = common.read(done_file)
    if (done.get('steps'), done.get('consumed')) != (369, 2945):
        raise ValueError('Only the actual fixed369/2945 final120 checkpoint is allowed')
    adapter_sha = done.get('adapter_sha256', '')
    if not re.fullmatch('[0-9a-f]{64}', adapter_sha) or not done.get('final_checkpoint'):
        raise ValueError('Final checkpoint path/SHA is missing')
    keys = common.rows(a.keys)
    by_id = {r['id']: r for r in keys}
    if len(keys) != len(by_id) or len(keys) != 1817:
        raise ValueError('Expected the complete, unique1817 development cohort')
    if (sum(r.get('old_panel') == 'natural' for r in keys),
            sum(r.get('old_panel') == 'pressure' for r in keys)) != (400, 100):
        raise ValueError('Old400/100 panel membership changed')
    target = sorted(r['id'] for r in keys if a.scope == 'selection1817'
                    or r.get('old_panel') in ('natural', 'pressure'))
    prior = collect(a.prior)
    if not prior or any(r['source_adapter_sha256'] != adapter_sha for r in prior):
        raise ValueError('Prior first receipts must come from this final120 adapter')
    needed = remaining_ids(target, prior)  # Invalid first receipts are also completed IDs.
    inputs = common.rows(a.inputs)
    lookup = {r['id']: r for r in inputs}
    if len(lookup) != len(inputs) or set(lookup) != set(by_id):
        raise ValueError('Original complete1817 GT-free input IDs differ')
    selected = []
    for i in needed:
        row = lookup[i]
        if {'GT', 'human_gt', 'answer', 'verdict', 'panel', 'sid'} & set(row):
            raise ValueError('Inference inputs must remain GT-free')
        selected.append({key: row[key] for key in ('id', 'claim', 'reference', 'expected_prompt_sha256')})
    for receipt in prior:
        if receipt['source_prompt_sha256_104'] != lookup[receipt['id']]['expected_prompt_sha256']:
            raise ValueError('Prior receipt does not use the unchanged104 input')
    bundle = a.bundle.resolve()
    relative = Path('data')/('full_pool_sft120_'+a.scope)
    folder = bundle/relative
    session_source = resolve(original['session_path'])
    if not session_source.exists():
        session_source = bundle/original['session_path']
    session = common.read(session_source)
    session_deadline(session)  # Validate, but never reset or extend the existing window.
    job = dict(name='full_pool_sft_'+a.scope, task=120, candidate='full_pool_sft',
               model_dir=original['model_dir'], final_adapter=done['final_checkpoint'],
               adapter_sha256=adapter_sha, inputs_path=str(relative/'inputs.jsonl').replace('\\', '/'),
               session_path=str(relative/'session.json').replace('\\', '/'),
               session_sha256=common.sha(session_source), scope=a.scope, ids=needed,
               target_N=len(target), prior_N=len(prior), prior_invalid_N=sum(not r['valid'] for r in prior),
               N=len(needed), max_seq_length=original['max_seq_length'], seed=original['seed'],
               evaluation=dict(batch_size=2, max_new_tokens=384, do_sample=False, num_beams=1,
                               repetition_penalty=1., parser='parse105.parse'),
               phase_limit_seconds=original['phase_limit_seconds'], save_reserve_seconds=180,
               no_training=True, no_shutdown=True, first_receipts_only=True)
    folder.mkdir(parents=True, exist_ok=True)
    # Freeze extension inputs/job, retaining the exact active session bytes.
    common.frozen(folder/'session.json', session_source.read_bytes())
    payload = ''.join(common.canonical(r)+'\n' for r in selected).encode('utf-8')
    common.frozen(folder/'inputs.jsonl', payload)
    common.frozen(folder/'job.json', (json.dumps(job, ensure_ascii=False, indent=2)+'\n').encode())
    summary = dict(scope=a.scope, target_N=len(target), first_receipts_N=len(prior),
                   invalid_first_receipts_not_retried=job['prior_invalid_N'], new_calls=len(needed),
                   job_path=str(folder/'job.json'), session_deadline_epoch=session_deadline(session),
                   session_unchanged=True, GPU_started=False)
    common.put(PRIVATE/('extension_'+a.scope+'_prepared.json'), summary)
    print(common.canonical(summary))


def worker(job_path):
    global STOP
    STOP = False
    def stop(*_):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    job = common.read(job_path)
    out = ROOT/'results'/job['name']
    out.mkdir(parents=True, exist_ok=True)
    session_path = resolve(job['session_path'])
    if common.sha(session_path) != job['session_sha256']:
        raise ValueError('Frozen active session changed; prepare a fresh explicit extension job')
    session = common.read(session_path)
    started = time.time()
    deadline = min(session_deadline(session), started+job['phase_limit_seconds'])-job['save_reserve_seconds']
    def budget(seconds=0):
        if STOP or time.time()+seconds >= deadline:
            raise TimeoutError('Current session/phase cutoff reached; preserve committed first receipts')
    def progress(stage, n, eta=None):
        common.put(out/'progress.json', dict(stage=stage, completed=n, total=job['N'],
            remaining_seconds=eta, epoch=time.time(), worker_elapsed_seconds=time.time()-started,
            window_GPU_estimate_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,
            no_shutdown=True))
    stage = 'prepare'
    try:
        budget(120)
        if job['evaluation'] != dict(batch_size=2, max_new_tokens=384, do_sample=False, num_beams=1,
                                    repetition_penalty=1., parser='parse105.parse'):
            raise ValueError('Frozen evaluation interface changed')
        rows = common.rows(resolve(job['inputs_path']))
        lookup = {r['id']: r for r in rows}
        if [r['id'] for r in rows] != job['ids'] or len(lookup) != job['N']:
            raise ValueError('Extension IDs differ from frozen missing-ID request')
        if any({'GT', 'human_gt', 'answer', 'verdict', 'panel', 'sid'} & set(r) for r in rows):
            raise ValueError('Inference inputs contain prohibited evaluation labels')
        adapter = resolve(job['final_adapter'])
        if common.sha(adapter/'adapter_model.safetensors') != job['adapter_sha256']:
            raise ValueError('Final120 adapter differs')
        fingerprint = dict(task=120, name=job['name'], adapter_sha256=job['adapter_sha256'],
                           job_sha256=common.sha(job_path), session_sha256=job['session_sha256'])
        identity = out/'identity.json'
        if identity.exists() and common.read(identity) != fingerprint:
            raise ValueError('Result directory belongs to another fixed120 extension')
        common.put(identity, fingerprint)
        prior = collect([out])
        if any(r['source_adapter_sha256'] != job['adapter_sha256'] for r in prior):
            raise ValueError('Existing extension receipts use another checkpoint')
        pending = remaining_ids(job['ids'], prior)
        if not pending:
            common.put(out/'complete.json', dict(N=job['N'], adapter_sha256=job['adapter_sha256'],
                       first_receipts=True, no_shutdown=True, epoch=time.time()))
            progress('complete', job['N'], 0); return
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                          TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',
                          TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
        from unsloth import FastLanguageModel as Fast
        import torch
        from transformers import AutoTokenizer
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        from data105 import shared
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('Original BF16 CUDA environment is required')
        stage = 'loading'
        progress(stage, len(prior))
        tokenizer = AutoTokenizer.from_pretrained(job['model_dir'], local_files_only=True)
        encoded = {r['id']: shared.prompt_ids(tokenizer, r) for r in rows}
        for i, ids in encoded.items():
            if common.digest(common.canonical(ids)) != lookup[i]['expected_prompt_sha256']:
                raise ValueError('Original104 prompt token identity changed: '+i)
            if len(ids)+384 > job['max_seq_length']:
                raise ValueError('Complete prompt plus output allowance exceeds context: '+i)
        model, _ = Fast.from_pretrained(model_name=job['model_dir'], max_seq_length=job['max_seq_length'],
            dtype=torch.bfloat16, load_in_4bit=False, load_in_8bit=False, full_finetuning=False,
            device_map={'': 0}, trust_remote_code=False, local_files_only=True)
        cfg = common.read(adapter/'adapter_config.json')
        model = Fast.get_peft_model(model, r=cfg['r'], lora_alpha=cfg['lora_alpha'],
            lora_dropout=cfg.get('lora_dropout', 0.), bias=cfg.get('bias', 'none'),
            target_modules=cfg['target_modules'], use_gradient_checkpointing=True,
            random_state=job['seed'], use_rslora=cfg.get('use_rslora', False),
            finetune_vision_layers=False, finetune_language_layers=True)
        restored = set_peft_model_state_dict(model, load_file(str(adapter/'adapter_model.safetensors')))
        if any('lora_' in k for k in getattr(restored, 'missing_keys', ())) or getattr(restored, 'unexpected_keys', ()):
            raise ValueError('Final120 LoRA failed to load exactly')
        if getattr(model, 'is_loaded_in_4bit', False) or getattr(model, 'is_loaded_in_8bit', False):
            raise ValueError('Quantization is not allowed')
        Fast.for_inference(model)
        model.eval()
        model.requires_grad_(False)
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
        if type(eos) is not int or eos < 0:
            raise ValueError('Original stop token is unavailable')
        order = sorted(pending, key=lambda i: (len(encoded[i]), i))
        batches = [order[n:n+2] for n in range(0, len(order), 2)]
        first = max((int(p.stem) for p in (out/'batches').glob('*.json') if p.stem.isdigit()), default=-1)+1
        completed, generated, total_seconds = len(prior), 0, 0.
        for number, identifiers in enumerate(batches, first):
            budget(40)
            stage = 'evaluation'
            eta = total_seconds/generated*(job['N']-completed) if generated else None
            progress(stage, completed, eta)
            began = time.perf_counter()
            common.put(out/'inflight.json', dict(ids=identifiers, epoch=time.time(), fingerprint=fingerprint))
            width = max(len(encoded[i]) for i in identifiers)
            ids = torch.tensor([[pad]*(width-len(encoded[i]))+encoded[i] for i in identifiers], device='cuda')
            mask = torch.tensor([[0]*(width-len(encoded[i]))+[1]*len(encoded[i]) for i in identifiers], device='cuda')
            with torch.inference_mode():
                outputs = model.generate(input_ids=ids, attention_mask=mask, do_sample=False, num_beams=1,
                    num_return_sequences=1, max_new_tokens=384, repetition_penalty=1., use_cache=True,
                    pad_token_id=pad, eos_token_id=eos)
            records = []
            for index, identifier in enumerate(identifiers):
                tail = outputs[index, width:].tolist()
                finish = 'length'
                if eos in tail:
                    tail = tail[:tail.index(eos)+1]
                    finish = 'stop'
                content = tokenizer.decode(tail, skip_special_tokens=True)
                records.append(dict(id=identifier, content=content, finish_reason=finish,
                    parsed=parse(content, finish), input_tokens=len(encoded[identifier]),
                    source_prompt_sha256_104=lookup[identifier]['expected_prompt_sha256'],
                    adapter_sha256=job['adapter_sha256']))
            path = out/'batches'/f'{number:04d}.json'
            if path.exists():
                raise FileExistsError('Never overwrite a committed first batch: '+str(path))
            seconds = time.perf_counter()-began
            common.put(path, dict(ids=identifiers, records=records, fingerprint=fingerprint, batch_seconds=seconds))
            (out/'inflight.json').unlink(missing_ok=True)
            completed += len(identifiers)
            generated += len(identifiers)
            total_seconds += seconds
            del ids, mask, outputs
        assert completed == job['N']
        common.put(out/'complete.json', dict(N=completed, adapter_sha256=job['adapter_sha256'],
                   first_receipts=True, no_shutdown=True, epoch=time.time()))
        progress('complete', completed, 0)
    except BaseException as error:
        common.put(out/'failure.json', dict(stage=stage, error_type=type(error).__name__, error=str(error),
                   first_receipts_preserved=True, no_shutdown=True, epoch=time.time()))
        raise


def guarded_run(job_path):
    if sys.platform != 'linux':
        raise RuntimeError('GPU extension run belongs only on the authorized Linux instance')
    job_path = resolve(job_path)
    job = common.read(job_path)
    session_path = resolve(job['session_path'])
    if common.sha(session_path) != job['session_sha256']:
        raise ValueError('Current session no longer matches the frozen extension')
    remaining = min(session_deadline(common.read(session_path))-time.time(), job['phase_limit_seconds'])-60
    if remaining <= 180:
        raise TimeoutError('Not enough active session time to load and save')
    active = subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
    if active:
        raise RuntimeError('GPU already has a compute process; do not overlap another job')
    child = subprocess.Popen([sys.executable, '-B', '-u', __file__, '_worker', '--job', str(job_path)],
                             cwd=ROOT, start_new_session=True)
    try:
        code = child.wait(timeout=remaining)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        raise TimeoutError('Active session hard cutoff stopped extension compute; no shutdown sent')
    if code:
        raise RuntimeError('120 extension failed; inspect saved first receipts/failure log')


def self_test():
    prior = [dict(id='a', valid=True), dict(id='b', valid=False)]
    assert remaining_ids(['a', 'b', 'c'], prior) == ['c']
    try:
        remaining_ids(['a', 'b'], prior+[dict(id='a', valid=True)])
        raise AssertionError('Duplicate first receipt accepted')
    except ValueError:
        pass
    assert session_deadline(dict(start_epoch=100, duration_seconds=200, GPU_cap_CNY=1,
                                 hourly_CNY=36, no_shutdown=True)) == 200
    print(common.canonical(dict(PASS=True, invalid_first_receipts_not_retried=True,
          missing_IDs_only=True, current_session_budget_enforced=True, GPU_started=False)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('self-test')
    a = sub.add_parser('prepare')
    a.add_argument('--scope', choices=('old500', 'selection1817'), required=True)
    a.add_argument('--training-result', type=Path, required=True)
    a.add_argument('--prior', type=Path, nargs='+', required=True)
    a.add_argument('--training-job', type=Path, default=PRIVATE/'job.json')
    a.add_argument('--bundle', type=Path, default=PRIVATE/'bundle')
    a.add_argument('--keys', type=Path, default=ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    a.add_argument('--inputs', type=Path, default=ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')
    for action in ('run', '_worker'):
        sub.add_parser(action).add_argument('--job', type=Path, required=True)
    args = p.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'self-test':
        self_test()
    elif args.action == 'run':
        guarded_run(args.job)
    else:
        worker(resolve(args.job))


if __name__ == '__main__':
    main()
