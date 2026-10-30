"""Small full-reference107 prefill plus frozen CPU-head deployment check.

No training or cached-state substitution.  Cached labels are loaded only after
all live predictions.  This script never shuts down or releases the instance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/104_supervision_evidence'))
import training104 as original

STOP = False
PREFIX = (4754, 415, 8217, 3147)


def stop(*_):
    global STOP
    STOP = True


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT/path


def classify(state, hidden):
    from torch.nn import functional as F
    # Same FP32 StandardScaler and eval-mode Linear/ReLU/Linear as fit_mlp117.
    value = (hidden.float()-state['mean'])/state['scale']
    value = F.relu(F.linear(value, state['net.0.weight'], state['net.0.bias']))
    value = F.linear(value, state['net.3.weight'], state['net.3.bias'])
    probability = value.softmax(-1)[0].tolist()
    index = int(value.argmax(-1)[0])
    return dict(verdict=original.LABELS[index], valid=True,
                probabilities=dict(zip(original.LABELS, probability)), probabilities_calibrated=False)


def equal_mean(predictions, members):
    values = {label: sum(predictions[name]['probabilities'][label] for name in members)/len(members)
              for label in original.LABELS}
    winner = max(original.LABELS, key=values.get)
    return dict(verdict=winner, valid=True, probabilities=values, probabilities_calibrated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', default='data/e2e_check117.json')
    args = parser.parse_args()
    job = common.read(resolve(args.job))
    out = ROOT/'results'/job['name']
    out.mkdir(parents=True, exist_ok=True)
    if (out/'complete.json').exists() or list((out/'cases').glob('*.json')):
        raise FileExistsError('Preserve prior live measurements; do not silently replay them')
    started = time.time()
    session = common.read(resolve(job['session_path']))
    deadline = min(session['start_epoch']+session['duration_seconds'],
                   session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],
                   started+job['phase_limit_seconds']) - 30
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    common.put(out/'pid.json', dict(pid=os.getpid(), name=job['name'], start_epoch=started))
    common.put(out/'progress.json', dict(stage='loading', completed=0, total=job['N'], epoch=started))

    def budget(seconds=0):
        if STOP or time.time()+seconds >= deadline:
            raise TimeoutError('Deployment check boundary; preserve measurements, no shutdown')

    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',
                      TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
    budget(60)
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer
    from peft import PeftModel

    torch.set_num_threads(4)
    rows = common.rows(resolve(job['inputs']))
    assert len(rows) == len({row['id'] for row in rows}) == job['N']
    assert all(not {'GT', 'human_gt', 'sid', 'panel', 'answer', 'verdict'} & set(row) for row in rows)
    tokenizer = AutoTokenizer.from_pretrained(job['model_dir'], local_files_only=True)
    assert tuple(tokenizer.encode('{"verdict":"', add_special_tokens=False)) == PREFIX
    heads = {}
    for item in job['heads']:
        path = resolve(item['path'])
        assert common.sha(path) == item['sha256']
        saved = torch.load(path, map_location='cpu', weights_only=True)
        assert tuple(saved['labels']) == tuple(original.LABELS)
        assert saved['selected_epoch'] == item['epoch']
        cfg = saved['config']
        assert (cfg['feature'], cfg['hidden'], cfg['activation'], cfg['dropout']) == ('verdict_prefix', 128, 'ReLU', .1)
        state = {name: value.float().cpu() for name, value in saved['state_dict'].items()}
        assert all(torch.isfinite(value).all() for value in state.values())
        heads[item['name']] = state

    load_started = time.perf_counter()
    model, _ = Fast.from_pretrained(model_name=job['model_dir'], max_seq_length=job['max_seq_length'],
        dtype=torch.bfloat16, load_in_4bit=False, load_in_8bit=False, full_finetuning=False,
        device_map={'': 0}, trust_remote_code=False, local_files_only=True)
    adapter = resolve(job['adapter_path'])
    assert common.sha(adapter/'adapter_model.safetensors') == job['adapter_sha256']
    model = PeftModel.from_pretrained(model, adapter, is_trainable=False)
    Fast.for_inference(model); model.eval()
    assert not any(parameter.requires_grad for parameter in model.parameters())
    load_seconds = time.perf_counter()-load_started
    startup_seconds = time.time()-started
    backbone = model.get_base_model().model
    measured = []
    for number, row in enumerate(rows):
        budget(20)
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
        before = time.perf_counter()
        prompt = original.prompt_ids(tokenizer, row)
        assert common.digest(common.canonical(prompt)) == row['expected_prompt_sha256']
        sequence = prompt + list(PREFIX)
        assert len(sequence) <= job['max_seq_length']
        tokenization_seconds = time.perf_counter()-before
        ids = torch.tensor([sequence], device='cuda')
        mask = torch.ones_like(ids)
        prefill_start = time.perf_counter()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
            output = backbone(input_ids=ids, attention_mask=mask, use_cache=False, return_dict=True)
            hidden = output.last_hidden_state if hasattr(output, 'last_hidden_state') else output[0]
            state = hidden[:, -1].float().cpu()
        torch.cuda.synchronize()
        prefill_seconds = time.perf_counter()-prefill_start
        predictions = {}; head_times = {}
        with torch.inference_mode():
            for name, head in heads.items():
                begin_head = time.perf_counter()
                predictions[name] = classify(head, state)
                head_times[name] = time.perf_counter()-begin_head
            for name, members in job.get('equal_mean_heads', {}).items():
                assert members and set(members) <= set(heads) and name not in heads
                begin_head = time.perf_counter()
                predictions[name] = equal_mean(predictions, members)
                head_times[name] = time.perf_counter()-begin_head
        elapsed = time.perf_counter()-before
        record = dict(id=row['id'], input_tokens=len(sequence), prompt_tokens=len(sequence)-len(PREFIX),
                      tokenization_seconds=tokenization_seconds,
                      prefill_and_CPU_transfer_seconds=prefill_seconds, CPU_head_seconds=head_times,
                      raw_input_through_both_heads_seconds=elapsed,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      first_live_case=number == 0, predictions=predictions)
        common.put(out/'cases'/f'{number:02d}.json', record)
        measured.append(record)
        common.put(out/'progress.json', dict(stage='live_prefill', completed=number+1, total=len(rows),
                   epoch=time.time(), remaining_seconds=elapsed*(len(rows)-number-1)))
        del ids, mask, output, hidden, state
    # Expected cached predictions are not available to either live classifier.
    expected = common.read(resolve(job['cached_predictions']))
    checks = {}
    for name in [*heads, *job.get('equal_mean_heads', {})]:
        changed = []
        max_difference = 0.
        for row in measured:
            actual = row['predictions'][name]; old = expected[name][row['id']]
            if actual['verdict'] != old['verdict']:
                changed.append(row['id'])
            if old.get('probabilities'):
                max_difference = max(max_difference, max(abs(actual['probabilities'][label]-old['probabilities'][label])
                                                        for label in original.LABELS))
        checks[name] = dict(N=len(measured), label_agreements=len(measured)-len(changed),
                            changed_IDs=changed, max_probability_abs_difference=max_difference)
    times = [row['raw_input_through_both_heads_seconds'] for row in measured]
    summary = dict(N=len(measured), load_seconds=load_seconds, startup_seconds=startup_seconds,
                   total_worker_wall_seconds=time.time()-started,
                   median_raw_input_through_both_heads_seconds=statistics.median(times),
                   min_live_seconds=min(times), max_live_seconds=max(times),
                   max_peak_allocated_bytes=max(row['peak_allocated_bytes'] for row in measured),
                   consistency=checks, epoch=time.time(), no_shutdown=True,
                   measurement_scope='Original-reference tokenization, one live107 prefill, transfer, frozen CPU heads and fixed equal means; model loading separately timed; metadata-selected examples, not population throughput',
                   first_case_includes_first_use_overhead=True, cached_features_used_for_live_prediction=False,
                   new_training=False, new_API_calls=0)
    common.put(out/'complete.json', summary)
    print(common.canonical(summary))


if __name__ == '__main__':
    main()
