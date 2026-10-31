"""One native full_repeat generation per ID; no retries, training or fallback."""
from pathlib import Path
import json, os, signal, sys, time
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/105_brief_supervision'))
import common105 as c
from parse105 import parse as parse_content
from prompt139 import prompt_ids, assert_unchanged_rope
from budget139 import deadlines
STOP = False


def worker():
    signal.signal(signal.SIGTERM, lambda *_: globals().update(STOP=True))
    signal.signal(signal.SIGINT, lambda *_: globals().update(STOP=True))
    job, session = c.read(R / 'data/job.json'), c.read(R / 'data/session.json')
    assert job['task'] == 139 and job['variant'] == 'full_repeat'
    assert job['generation']['batch_size'] == 1 and job['max_seq_length'] == 32768
    out = R / 'results'; out.mkdir(exist_ok=True)
    started = time.time(); timing = deadlines(started, session, job); deadline = timing['compute_end']
    c.put(out / 'deadlines.json', dict(started=started, **timing))
    if timing['available_compute_seconds'] < 300:
        raise TimeoutError('Less than300 seconds computation plus900-second global save reserve')
    identity = dict(job_sha256=c.sha(R / 'data/job.json'), inputs_sha256=c.sha(R / job['inputs']))
    if (out / 'identity.json').exists() and c.read(out / 'identity.json') != identity:
        raise ValueError('Job/input identity changed')
    c.put(out / 'identity.json', identity)
    if (out / 'inflight.json').exists():
        raise RuntimeError('Uncommitted formal request: preserve and stop; no automatic resend')
    def progress(stage, **extra):
        count = len(list((out / 'full_repeat').glob('*.json')))
        c.put(out / 'progress.json', dict(stage=stage, completed=count, total=job['expected_N'],
            target_N=job['target_N'], prior_N=job['prior_N'], epoch=time.time(),
            elapsed_seconds=time.time()-started, compute_deadline=deadline,
            GPU_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,
            API_CNY=0, no_shutdown=True, **extra))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
        TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',
        TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
    progress('loading')
    from unsloth import FastLanguageModel as Fast
    import torch
    from transformers import AutoTokenizer, StoppingCriteria, StoppingCriteriaList
    from peft import PeftModel
    class Deadline(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            return torch.full((input_ids.shape[0],), STOP or time.time() >= deadline,
                              dtype=torch.bool, device=input_ids.device)
    inputs = {r['id']: r for r in c.rows(R / job['inputs'])}
    lengths = {r['id']: r for r in c.rows(R / 'data/lengths.jsonl')}
    assert len(inputs) == job['expected_N'] and set(inputs) == set(lengths)
    assert all(set(r) == {'id', 'claim', 'reference', 'prompt_token_sha256'} for r in inputs.values())
    tokenizer = AutoTokenizer.from_pretrained(job['model_dir'], local_files_only=True)
    encoded = {i: prompt_ids(tokenizer, r) for i, r in inputs.items()}
    for i, ids in encoded.items():
        assert c.digest(c.canonical(ids)) == inputs[i]['prompt_token_sha256']
        assert len(ids) == lengths[i]['input_tokens'] and len(ids) + 384 <= 32768
    order = sorted(inputs, key=lambda i: (-len(encoded[i]), i))
    assert order == job['ids'] and order[0] == job['first_formal_ID']
    model, _ = Fast.from_pretrained(model_name=job['model_dir'], max_seq_length=32768,
        dtype=torch.bfloat16, load_in_4bit=False, load_in_8bit=False,
        device_map={'': 0}, local_files_only=True)
    signature = assert_unchanged_rope(c.read(Path(job['model_dir'])/'config.json'), model.config.to_dict(), 32768)
    adapter = Path(job['adapter']) / 'adapter_model.safetensors'
    assert adapter.stat().st_size == job['adapter_bytes'] and c.sha(adapter) == job['adapter_sha256']
    c.put(out / 'runtime_model_guard.json', dict(status='PASS', rope=signature,
        source_adapter_sha256=job['adapter_sha256'], capacity=32768))
    model = PeftModel.from_pretrained(model, job['adapter'], adapter_name='full_repeat', is_trainable=False)
    Fast.for_inference(model); model.eval(); model.requires_grad_(False); model.set_adapter('full_repeat')
    eos = tokenizer.convert_tokens_to_ids('<|im_end|>'); pad = tokenizer.pad_token_id or tokenizer.eos_token_id
    generated = 0; seconds = 0.
    for i in order:
        dest = out / 'full_repeat' / (i + '.json')
        if dest.exists():
            raise FileExistsError('Formal first receipt exists: no automatic rerun/resume')
        if STOP or time.time() + 60 >= deadline:
            raise TimeoutError('Computation deadline reached; no new formal request')
        progress('inference', current_ID=i, remaining_seconds=(seconds/generated)*(len(order)-generated) if generated else None)
        c.put(out / 'inflight.json', dict(arm='full_repeat', ids=[i], epoch=time.time()))
        x = torch.tensor([encoded[i]], device='cuda'); mask = torch.ones_like(x)
        torch.cuda.synchronize(); began = time.perf_counter(); torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            result = model.generate(input_ids=x, attention_mask=mask, do_sample=False,
                num_beams=1, num_return_sequences=1, max_new_tokens=384, repetition_penalty=1.,
                use_cache=True, pad_token_id=pad, eos_token_id=eos,
                stopping_criteria=StoppingCriteriaList([Deadline()]))
        torch.cuda.synchronize(); elapsed = time.perf_counter()-began
        tail = result[0, len(encoded[i]):].tolist(); finish = 'length'
        if eos in tail:
            tail = tail[:tail.index(eos)+1]; finish = 'stop'
        if STOP or time.time() >= deadline:
            finish = 'budget_stop'
        content = tokenizer.decode(tail, skip_special_tokens=True)
        parsed = parse_content(content, finish); parsed['valid'] = bool(parsed['valid'] and finish == 'stop')
        c.put(dest, dict(id=i, arm='full_repeat', content=content, parsed=parsed, finish_reason=finish,
            input_tokens=len(encoded[i]), output_tokens=len(tail), total_answer_tokens=len(tail),
            prompt_token_sha256=inputs[i]['prompt_token_sha256'], adapter_sha256=job['adapter_sha256'],
            seconds=elapsed, batch_seconds=elapsed, batch_size=1,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), epoch=time.time()))
        (out / 'inflight.json').unlink(); generated += 1; seconds += elapsed
        del x, mask, result
    progress('complete', remaining_seconds=0)
    c.put(out / 'complete.json', dict(task=139, scope=job['scope'], N=generated,
        expected_N=job['expected_N'], epoch=time.time(), no_training=True, new_API=0, no_shutdown=True))


if __name__ == '__main__':
    try:
        worker()
    except BaseException as exc:
        c.put(R / 'results/failure.json', dict(type=type(exc).__name__, error=str(exc),
            epoch=time.time(), no_shutdown=True, automatic_retry=False))
        raise
