"""Future explicit GPU worker: one source120 forward per original prompt.

Import/help performs no model work. It generates no verdict/reason and never trains.
"""
from pathlib import Path
import argparse
import json
import inspect
import importlib.metadata
import math
import os
import signal
import subprocess
import sys
import time

STOP = False


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def append_event(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + '\n')
        handle.flush()


def execute(bundle, session_path, compute_seconds, save_seconds):
    global STOP
    bundle = Path(bundle).resolve()
    job = read(bundle / 'data/job.json')
    if job['adapter_sha256'] != '47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a':
        raise ValueError('Only the frozen120 final369 adapter is permitted')
    if not isinstance(job.get('compute_limit_seconds'), (int, float)) or not isinstance(job.get('save_reserve_seconds'), (int, float)):
        raise ValueError('Budget is not frozen; root must set compute and save limits before starting')
    if (job['max_seq_length'] != 16384 or not 0 < compute_seconds <= job['compute_limit_seconds']
            or save_seconds < job['save_reserve_seconds']):
        raise ValueError('Explicit bounded compute and at least180 seconds save reserve required')
    session = read(session_path)
    start = time.time()
    global_end = session['start_epoch'] + 3600 * session['GPU_cap_CNY'] / session['hourly_CNY']
    if 'duration_seconds' in session:
        global_end = min(global_end, session['start_epoch'] + session['duration_seconds'])
    deadline = min(start + compute_seconds, global_end - save_seconds)
    if deadline - start < 300:
        raise TimeoutError('Insufficient authorized window; do not load model')
    occupied = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
    if occupied:
        raise RuntimeError('GPU occupied; never overlap or terminate the active task')
    out = bundle.parent / 'results'
    if (out / 'inflight.json').exists():
        raise RuntimeError('Prior uncommitted forward must be inspected; no automatic resend')
    signal.signal(signal.SIGTERM, lambda *_: globals().update(STOP=True))
    signal.signal(signal.SIGINT, lambda *_: globals().update(STOP=True))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',
                      TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
    sys.path.insert(0, str(bundle / 'tasks/104_supervision_evidence'))
    sys.path.insert(0, str(bundle / 'tasks/136_claim_repeat_transfer'))
    sys.path.insert(0, str(bundle / 'tasks/105_brief_supervision'))
    import common105 as c
    import training104
    import prompt136
    for rel, expected in job.get('source_files_sha256', {}).items():
        if c.sha(bundle / rel) != expected:
            raise ValueError('Bundled source fingerprint changed: ' + rel)
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer
    from peft import PeftModel
    records = [json.loads(s) for s in (bundle / job['input']).read_text(encoding='utf-8').splitlines() if s.strip()]
    if len(records) != job['expected_N'] or len({(r['variant'], r['id']) for r in records}) != len(records):
        raise ValueError('Duplicate or missing variant/ID input')
    if {(r['variant'],r['id']) for r in records} != {(v,i) for v, ids in job['score_ids_by_variant'].items() for i in ids}:
        raise ValueError('Inputs differ from frozen per-variant score targets')
    tokenizer = AutoTokenizer.from_pretrained(job['model_dir'], local_files_only=True)
    prefix = tokenizer.encode(job['prefix'], add_special_tokens=False)
    if prefix != job['prefix_token_ids']:
        raise ValueError('Canonical JSON prefix tokenizer changed')
    if tokenizer.encode('Supported', add_special_tokens=False)[0] != job['branch_ids']['S']:
        raise ValueError('Supported token identity changed')
    if tokenizer.encode('Not Supported', add_special_tokens=False)[0] != job['branch_ids']['Not']:
        raise ValueError('Not token identity changed')
    encoded = {}
    manifest = []
    for r in records:
        if set(r) != {'id', 'variant', 'claim', 'reference', 'expected_prompt_token_sha256', 'expected_prompt_tokens'}:
            raise ValueError('Score input must contain no GT or supplied verdict')
        if r['variant'] not in job['variants']:
            raise ValueError('Unknown frozen prompt variant')
        prompt = (training104.prompt_ids(tokenizer, r) if r['variant'] == 'native120' else prompt136.prompt_ids(tokenizer, r))
        if (c.digest(c.canonical(prompt)) != r['expected_prompt_token_sha256']
                or len(prompt) != r['expected_prompt_tokens'] or len(prompt) + len(prefix) > job['max_seq_length']):
            raise ValueError('Original prompt fingerprint/length changed')
        encoded[(r['variant'], r['id'])] = prompt + prefix
        manifest.append(dict(id=r['id'], variant=r['variant'], prompt_token_sha256=r['expected_prompt_token_sha256'],
                             original_prompt_tokens=len(prompt), prefix_token_ids=prefix,
                             scoring_input_token_sha256=c.digest(c.canonical(prompt + prefix))))
    out.mkdir(parents=True, exist_ok=True)
    manifest_text = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in manifest)
    manifest_path = out / 'encoded_manifest.jsonl'
    if manifest_path.exists() and manifest_path.read_text(encoding='utf-8') != manifest_text:
        raise ValueError('Existing encoded scoring manifest differs')
    manifest_path.write_text(manifest_text, encoding='utf-8', newline='\n')
    reused = {}
    reuse_root = bundle / job['reuse_results'] if job.get('reuse_results') else None
    expected_reused = {(v,i) for v,ids in job.get('reused_score_ids_by_variant',{}).items() for i in ids}
    if reuse_root is not None:
        for item in read(reuse_root/'provenance.json'):
            key = (item['variant'],item['id'])
            source = bundle / item['copied_path']
            if key not in encoded or c.sha(source) != item['source_sha256']:
                raise ValueError('Copied reusable score fingerprint changed')
            row = read(source)
            if (row.get('adapter_sha256') != job['adapter_sha256']
                    or row.get('scoring_input_token_sha256') != c.digest(c.canonical(encoded[key]))
                    or row.get('prefix_token_ids') != prefix
                    or not math.isfinite(row.get('logit_S_minus_Not',float('nan')))):
                raise ValueError('Reusable score differs from this exact scoring input')
            reused[key] = row
    if set(reused) != expected_reused:
        raise ValueError('Frozen reusable score inventory differs')
    model_load_start = time.time()
    checkpoint = Path(job['adapter']) / 'adapter_model.safetensors'
    if checkpoint.stat().st_size != job['adapter_bytes'] or c.sha(checkpoint) != job['adapter_sha256']:
        raise ValueError('Actual source120 adapter does not match frozen identity')
    if STOP or time.time() + 90 >= deadline:
        raise TimeoutError('Insufficient time for model loading; no forward started')
    model, _ = Fast.from_pretrained(model_name=job['model_dir'], max_seq_length=16384, dtype=torch.bfloat16,
                                    load_in_4bit=False, load_in_8bit=False, full_finetuning=False, trust_remote_code=False,
                                    device_map={'': 0}, local_files_only=True)
    model = PeftModel.from_pretrained(model, job['adapter'], adapter_name='source120', is_trainable=False)
    Fast.for_inference(model); model.eval(); model.requires_grad_(False); model.set_adapter('source120')
    base = model.get_base_model()
    identity = dict(adapter_sha256=job['adapter_sha256'], job_sha256=c.sha(bundle / 'data/job.json'),
                    input_sha256=c.sha(bundle / job['input']), prefix_token_ids=prefix, branch_ids=job['branch_ids'])
    if (out / 'identity.json').exists() and read(out / 'identity.json') != identity:
        raise ValueError('Existing output identity differs; preserve it and stop')
    parameters = inspect.signature(base.forward).parameters
    if 'logits_to_keep' not in parameters:
        raise RuntimeError('Loaded patched forward lacks explicit logits_to_keep; no unsafe fallback')
    def last_position_only(module, args):
        state = args[0]
        if not ((state.ndim == 3 and tuple(state.shape[:2]) == (1, 1))
                or (state.ndim == 2 and state.shape[0] == 1)):
            raise RuntimeError('LM head must receive exactly one final position before vocabulary projection')
    base.lm_head.register_forward_pre_hook(last_position_only)
    put(out / 'identity.json', identity)
    put(out / 'runtime.json', dict(forward_signature=str(inspect.signature(base.forward)),
                                  versions={v: importlib.metadata.version(v) for v in ('torch','transformers','unsloth','unsloth_zoo','peft')},
                                  logits_to_keep=1, output_hidden_states=False,
                                  model_load_seconds=time.time()-model_load_start, preparation_seconds=model_load_start-start))
    elapsed = []
    for r in records:
        key = (r['variant'], r['id'])
        if key in reused:
            continue
        path = out / r['variant'] / (r['id'] + '.json')
        if path.exists():
            old = read(path)
            if (old.get('adapter_sha256') != job['adapter_sha256'] or old.get('variant') != r['variant']
                    or old.get('prompt_token_sha256') != r['expected_prompt_token_sha256']
                    or old.get('prefix_token_ids') != prefix or old.get('id') != r['id']
                    or not math.isfinite(old.get('logit_S_minus_Not', float('nan')))):
                raise ValueError('Existing score belongs to another identity')
            continue
        if STOP or time.time() + 30 >= deadline:
            raise TimeoutError('Stop before next forward; retain formal pilot scores')
        attempt = dict(id=r['id'], variant=r['variant'], epoch=time.time(), event='started',
                       prompt_tokens=r['expected_prompt_tokens'], scoring_tokens=len(encoded[key]))
        put(out / 'inflight.json', attempt)
        append_event(out / 'attempts.jsonl', attempt)
        x = torch.tensor([encoded[key]], device='cuda')
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); began = time.perf_counter()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
            output = base(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False,
                          return_dict=True, logits_to_keep=1, output_hidden_states=False, output_attentions=False)
            if output.logits.ndim != 3 or tuple(output.logits.shape[:2]) != (1, 1):
                raise RuntimeError('Expected only final-position full-vocabulary logits')
            logits = output.logits[0, 0].float()
            probabilities = torch.softmax(logits, dim=-1)
            s_logit = float(logits[job['branch_ids']['S']])
            not_logit = float(logits[job['branch_ids']['Not']])
            margin = s_logit - not_logit
            p_s = float(probabilities[job['branch_ids']['S']])
            p_not = float(probabilities[job['branch_ids']['Not']])
        torch.cuda.synchronize(); seconds = time.perf_counter() - began
        if not (all(math.isfinite(v) for v in (s_logit, not_logit, margin))
                and all(math.isfinite(v) and 0 <= v <= 1 for v in (p_s, p_not)) and 0 < p_s + p_not <= 1 + 1e-6):
            raise FloatingPointError('Invalid branch probabilities; do not fill from another prompt')
        put(path, dict(id=r['id'], variant=r['variant'], adapter_sha256=job['adapter_sha256'],
                       prompt_token_sha256=r['expected_prompt_token_sha256'], original_prompt_tokens=r['expected_prompt_tokens'],
                       prefix_token_ids=prefix, scoring_input_token_sha256=c.digest(c.canonical(encoded[key])),
                       branch_logits={'S': s_logit, 'Not': not_logit}, logit_S_minus_Not=margin,
                       first_branch={'S': p_s, 'Not': p_not}, conditional_S_given_S_or_Not=p_s/(p_s+p_not),
                       branch_probability_mass=p_s+p_not, other_token_mass=max(0., 1-p_s-p_not),
                       seconds=seconds, batch_size=1, max_seq_length=16384, dtype='bfloat16',
                       peak_allocated_bytes=torch.cuda.max_memory_allocated(), no_generated_verdict=True, no_generated_reason=True))
        append_event(out / 'attempts.jsonl', dict(id=r['id'], variant=r['variant'], epoch=time.time(),
                     event='completed', seconds=seconds, prompt_tokens=r['expected_prompt_tokens'],
                     scoring_tokens=len(encoded[key])))
        (out / 'inflight.json').unlink(); elapsed.append(dict(seconds=seconds, prompt_tokens=r['expected_prompt_tokens']))
        del x, output, logits, probabilities
    put(out / 'complete.json', dict(scope=job['scope'], expected_N=len(records), retained_scores=len(records),
                                    reused_score_N=len(reused), new_forwards=len(elapsed),
                                    new_forward_seconds=sum(r['seconds'] for r in elapsed),
                                    worker_started_epoch=start, worker_completed_epoch=time.time(),
                                    worker_wall_seconds=time.time()-start, no_training=True,
                                    no_verdict_or_reason_changes=True, no_shutdown=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Explicit GPU execution; never used by CPU preparation')
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--session', type=Path)
    parser.add_argument('--compute-seconds', type=int)
    parser.add_argument('--save-reserve-seconds', type=int, default=180)
    args = parser.parse_args()
    if not args.execute:
        print('Prepared only. GPU execution requires --execute, original --session and explicit --compute-seconds.')
        return
    if args.session is None or args.compute_seconds is None:
        parser.error('--execute requires an existing authorized session and explicit compute seconds')
    began = time.time()
    status = 'failed'
    scope = read(args.bundle.resolve()/'data/job.json').get('scope')
    try:
        execute(args.bundle, args.session, args.compute_seconds, args.save_reserve_seconds)
        status = 'complete'
    finally:
        put(args.bundle.resolve().parent / 'results/run_exit.json',
            dict(status=status, worker_started_epoch=began, worker_completed_epoch=time.time(),
                 worker_wall_seconds=time.time()-began, scope=scope, no_shutdown=True))


if __name__ == '__main__':
    main()
