"""Conditional full-pool original-interface SFT; no model/GPU activity on import."""
from pathlib import Path
import argparse
from collections import Counter
import os
import random
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
from data105 import encode, shared, training_plan
from parse105 import parse

STOP = False


def stop(*_):
    global STOP
    STOP = True


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('ab') as stream:
        stream.write((common.canonical(value)+'\n').encode())
        stream.flush()


def run(job, out):
    global STOP
    STOP = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    session = common.read(resolve(job['session_path']))
    started = time.time()
    deadline = min(session['start_epoch']+session['duration_seconds'],
                   session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],
                   started+job['phase_limit_seconds']) - job['save_reserve_seconds']
    work = out / 'train'
    work.mkdir(parents=True, exist_ok=True)
    optimizer = scheduler = model = None
    save_current = None
    step = consumed = 0
    partial = updating = False
    partial_rng = None
    stage = 'preparing'

    def budget(seconds=0):
        if STOP or time.time()+seconds >= deadline:
            raise TimeoutError('Insufficient phase/window time; preserve full scope and checkpoint')

    def progress(value, n, total, eta=None):
        nonlocal stage
        stage = value
        common.put(out / 'progress.json', dict(stage=value, completed=n, total=total,
                   remaining_seconds=eta, epoch=time.time(),
                   worker_elapsed_seconds=time.time()-started,
                   window_GPU_estimate_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,
                   no_shutdown=True))

    try:
        tr = job['training']
        assert (tr['N'], tr['epochs'], tr['total_steps'], tr['microbatch'],
                tr['gradient_accumulation'], tr['learning_rate']) == (2945, 2, 518, 1, 8, 1e-5)
        assert not tr['fresh_Adam'] and tr['loss'] == 'unchanged loss105.backbone_loss'
        train_path = resolve(job['train_path'])
        rows = common.rows(train_path)
        lengths = {r['id']: r for r in common.rows(resolve(job['lengths_path']))}
        plan = training_plan([r['id'] for r in rows], 2, 8)[:518]
        assert len(rows) == len({r['id'] for r in rows}) == 2945
        assert len(plan) == 518 and plan[-1]['consumed'] == 4137 and plan[-1]['loss_divisor'] == 8
        assert plan == common.read(resolve(job['plan_path']))
        initial_estimate = (job['expected_seconds_per_example']*job['additional_presentations'] +
                            job['expected_screen_seconds'] + job['load_and_gate_reserve_seconds'])
        if not (work / 'resume.json').exists():
            budget(initial_estimate)
        else:
            budget(90)
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          HF_HUB_DISABLE_TELEMETRY='1',
                          TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',
                          TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
        from unsloth import FastLanguageModel as Fast
        import torch
        import numpy as np
        from transformers import AutoTokenizer
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        from loss105 import backbone_loss
        sys.path.insert(0, str(ROOT / 'tasks/107_support_aux'))
        import checkpoint107 as checkpoint

        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('BF16 CUDA required; no quantized/offloaded fallback')
        random.seed(job['seed'])
        np.random.seed(job['seed'])
        torch.manual_seed(job['seed'])
        torch.cuda.manual_seed_all(job['seed'])
        progress('loading', 0, 518, initial_estimate)
        tokenizer = AutoTokenizer.from_pretrained(job['model_dir'], local_files_only=True)
        encoded = {}
        for row in rows:
            item = encode(tokenizer, row)
            expected = lengths[row['id']]
            assert item['prompt_token_sha256'] == expected['prompt_token_sha256']
            assert item['answer_sha256'] == expected['answer_sha256']
            assert len(item['input_ids']) == expected['total_tokens'] <= job['max_seq_length']
            item.pop('labels')
            encoded[row['id']] = item
        screens = common.rows(resolve(job['screen_inputs_path']))
        assert len(screens) == len({r['id'] for r in screens}) == 160
        assert not {r['id'] for r in screens} & set(encoded)
        assert all(not {'GT', 'sid', 'panel', 'answer', 'verdict'} & set(r) for r in screens)
        screen_lengths = {r['id']: r for r in common.rows(resolve(job['screen_lengths_path']))}
        if job['input_transform'] == 'claim_repeat':
            sys.path.insert(0, str(ROOT/'tasks/136_claim_repeat_transfer'))
            from prompt136 import prompt_ids as evaluation_prompt_ids
        elif job['input_transform'] == 'original':
            evaluation_prompt_ids = shared.prompt_ids
        else:
            raise ValueError('Unfrozen evaluation input')
        screen_ids = {r['id']: evaluation_prompt_ids(tokenizer, r) for r in screens}
        for identifier, ids in screen_ids.items():
            assert common.digest(common.canonical(ids)) == screen_lengths[identifier]['prompt_token_sha256']
            assert len(ids)+384 <= job['max_seq_length']
        source = resolve(job['source120_adapter'])
        assert common.sha(source/'adapter_model.safetensors') == job['source_adapter_sha256']
        adapter = common.read(source/'adapter_config.json')
        model, _ = Fast.from_pretrained(
            model_name=job['model_dir'], max_seq_length=job['max_seq_length'], dtype=torch.bfloat16,
            load_in_4bit=False, load_in_8bit=False, full_finetuning=False, device_map={'': 0},
            trust_remote_code=False, local_files_only=True)
        model = Fast.get_peft_model(
            model, r=adapter['r'], lora_alpha=adapter['lora_alpha'],
            lora_dropout=adapter.get('lora_dropout', 0.), bias=adapter.get('bias', 'none'),
            target_modules=adapter['target_modules'], use_gradient_checkpointing=True,
            random_state=job['seed'], use_rslora=adapter.get('use_rslora', False),
            finetune_vision_layers=False, finetune_language_layers=True)

        def restore(folder):
            result = set_peft_model_state_dict(model, load_file(str(folder/'adapter_model.safetensors')))
            if (any('lora_' in name for name in getattr(result, 'missing_keys', ())) or
                    getattr(result, 'unexpected_keys', ())):
                raise ValueError('Source/resume LoRA keys do not match')

        restore(source)
        Fast.for_training(model)
        named = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
        params = [p for name, p in named]
        assert sum(p.numel() for p in params) == 43278336
        assert all('lora_' in name and 'vision' not in name and 'visual' not in name for name, p in named)
        assert any(bool(p.detach().count_nonzero()) for name, p in named if 'lora_B' in name)
        assert all(p.device.type == 'cuda' for p in model.parameters())
        assert not getattr(model, 'is_loaded_in_4bit', False) and not getattr(model, 'is_loaded_in_8bit', False)
        optimizer = torch.optim.AdamW(params, lr=1e-5, betas=tuple(tr['betas']),
                                      eps=tr['eps'], weight_decay=0.)
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.)
        assert not optimizer.state
        fingerprint = dict(task=job['task'], candidate=job['name'],
                           train=common.sha(train_path), job=common.digest(common.canonical(job)),
                           source120=job['source_adapter_sha256'], code=common.sha(Path(__file__)))
        common.put(out/'setup.json', dict(fingerprint=fingerprint, N=2945, steps=518,
                   source120_continuation=True, fresh_Adam=False, class_weights=False,
                   auxiliary_head=False, objective='loss105.backbone_loss',
                   LoRA_dtypes=dict(Counter(str(p.dtype) for p in params)), backbone_BF16=True,
                   no_input_truncation=True, checkpoint_selection='fixed_final518'))

        def capture_rng():
            return torch.get_rng_state(), torch.cuda.get_rng_state_all(), random.getstate(), np.random.get_state()

        def restore_rng(state):
            torch.set_rng_state(state[0])
            torch.cuda.set_rng_state_all(state[1])
            random.setstate(state[2])
            np.random.set_state(state[3])

        def tensor(item):
            return dict(input_ids=torch.tensor([item['input_ids']], device='cuda'),
                        attention_mask=torch.ones((1, len(item['input_ids'])), dtype=torch.long, device='cuda'),
                        groups=torch.tensor([item['groups']], device='cuda'))

        def save():
            return checkpoint.save(model, optimizer, scheduler, work, step, consumed, fingerprint)

        save_current = save
        if (work/'resume.json').exists():
            step, consumed, _ = checkpoint.load(optimizer, scheduler, work, fingerprint, restore)
            assert 0 <= step <= 518 and consumed == (plan[step-1]['consumed'] if step else 0)
        else:
            source_work = resolve(job['source_work'])
            source_pointer = common.read(source_work/'resume.json')
            assert source_pointer['fingerprint'] == job['source_fingerprint']
            step, consumed, _ = checkpoint.load(optimizer, scheduler, source_work, source_pointer['fingerprint'], restore)
            assert (step, consumed) == (369, 2945)
            common.put(out/'continuation_origin.json', dict(source_step=step, source_consumed=consumed,
                source_fingerprint=source_pointer['fingerprint'], optimizer_scheduler_rng_restored=True,
                source_checkpoint_unchanged=True, additional_steps=149, target_step=518))
            save()
        assert all(g['lr'] == g['initial_lr'] == 1e-5 for g in optimizer.param_groups)
        if not (out/'gpu_gate.json').exists():
            budget(90)
            progress('longest_original_loss_backward', step, 518)
            identifier = max(encoded, key=lambda i: len(encoded[i]['input_ids']))
            partial_rng = capture_rng()
            partial = True
            reserve = [] if optimizer.state else [torch.zeros_like(p) for p in params for _ in range(2)]
            batch = tensor(encoded[identifier])
            torch.cuda.reset_peak_memory_stats()
            began = time.perf_counter()
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss, info = backbone_loss(model, batch, chunk_tokens=16)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(params, 1.)
            torch.cuda.synchronize()
            assert bool(torch.isfinite(loss) and torch.isfinite(norm)) and float(norm) > 0
            assert any(p.grad is not None and bool(p.grad.count_nonzero()) for p in params)
            free, total = torch.cuda.mem_get_info()
            external = max(0, total-free-torch.cuda.memory_reserved())
            margin = total-external-torch.cuda.max_memory_allocated()
            assert margin >= 256*1024**2, 'Longest original-loss backward has insufficient memory margin'
            common.put(out/'gpu_gate.json', dict(fingerprint=fingerprint, id=identifier,
                       prompt_tokens=encoded[identifier]['prompt_tokens'],
                       total_tokens=len(encoded[identifier]['input_ids']), original_loss_info=info,
                       seconds=time.perf_counter()-began, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                       headroom_bytes=margin, LoRA_gradient=True, optimizer_updates=0,
                       optimizer_resumed=True, no_truncation=True))
            del reserve, batch, loss
            optimizer.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
            restore_rng(partial_rng)
            partial = False
        else:
            assert common.read(out/'gpu_gate.json')['fingerprint'] == fingerprint
        train_start = time.perf_counter()
        starting_consumed = consumed
        starting_tokens = sum(lengths[i]['total_tokens'] for p in plan[:step] for i in p['ids'])
        all_tokens = sum(lengths[i]['total_tokens'] for entry in plan for i in entry['ids'])
        seen_tokens = starting_tokens
        for entry in plan[step:]:
            budget(30)
            progress('training', step, 518)
            partial_rng = capture_rng()
            partial = True
            optimizer.zero_grad(set_to_none=True)
            began = time.perf_counter()
            losses = []
            tokens = 0
            for identifier in entry['ids']:
                budget(10)
                batch = tensor(encoded[identifier])
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    loss, _ = backbone_loss(model, batch, chunk_tokens=16)
                assert bool(torch.isfinite(loss))
                (loss/entry['loss_divisor']).backward()
                losses.append(float(loss.detach()))
                tokens += lengths[identifier]['total_tokens']
                del batch, loss
            norm = torch.nn.utils.clip_grad_norm_(params, 1.)
            assert bool(torch.isfinite(norm))
            updating = True
            optimizer.step()
            scheduler.step()
            torch.cuda.synchronize()
            step, consumed = entry['step'], entry['consumed']
            updating = partial = False
            assert optimizer.param_groups[0]['lr'] == 1e-5
            if step % 16 == 0 or step == 518:
                save()
            seen_tokens += tokens
            seconds = time.perf_counter()-began
            append(out/'steps.jsonl', dict(step=step, consumed=consumed, ids=entry['ids'],
                   loss_divisor=entry['loss_divisor'], loss=sum(losses)/len(losses),
                   gradient_norm=float(norm), tokens=tokens, seconds=seconds, lr=1e-5))
            rate = (time.perf_counter()-train_start)/max(1, seen_tokens-starting_tokens)
            eta = rate*(all_tokens-seen_tokens)*1.05 + job['expected_screen_seconds']
            progress('training', step, 518, eta)
            # Wall-clock guards at every microbatch enforce the hard cap.
            # Initial compilation must not turn a noisy ETA into premature cancellation.
            if consumed-starting_consumed >= 32 and step < 518:
                budget(60)
        assert (step, consumed) == (518, 4137)
        pointer = common.read(work/'resume.json')
        assert (pointer['step'], pointer['consumed']) == (518, 4137)
        folder = work/pointer['slot']
        complete = common.read(folder/'checkpoint_complete.json')
        adapter_sha = complete['files']['adapter_model.safetensors']
        common.put(out/'best.json', dict(step=518, checkpoint=str(folder), adapter_sha256=adapter_sha,
                   selection='fixed_final518; no development model selection'))
        common.put(out/'training_done.json', dict(steps=518, consumed=4137,
                   final_checkpoint=str(folder), adapter_sha256=adapter_sha,
                   fingerprint=fingerprint, epoch=time.time()))
        optimizer.zero_grad(set_to_none=True)
        optimizer = scheduler = None
        torch.cuda.empty_cache()
        Fast.for_inference(model)
        model.eval()
        order = sorted(screen_ids, key=lambda i: (len(screen_ids[i]), i))
        batches = [order[start:start+2] for start in range(0, len(order), 2)]
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
        done = 0
        for number, identifiers in enumerate(batches):
            path = out/'batches'/f'{number:04d}.json'
            if path.exists():
                old = common.read(path)
                assert old['ids'] == identifiers and old['fingerprint'] == fingerprint
                for record in old['records']:
                    dest=out/'predictions'/(record['id']+'.json')
                    if dest.exists():
                        assert common.read(dest)['content']==record['content']
                    else:
                        common.put(dest,record)
                done += len(identifiers)
                continue
            budget(20)
            progress('fixed160_evaluation', done, 160)
            width = max(len(screen_ids[i]) for i in identifiers)
            inputs = torch.tensor([[pad]*(width-len(screen_ids[i]))+screen_ids[i] for i in identifiers], device='cuda')
            mask = torch.tensor([[0]*(width-len(screen_ids[i]))+[1]*len(screen_ids[i]) for i in identifiers], device='cuda')
            with torch.inference_mode():
                outputs = model.generate(input_ids=inputs, attention_mask=mask, do_sample=False,
                    num_beams=1, num_return_sequences=1, max_new_tokens=384,
                    repetition_penalty=1., use_cache=True, pad_token_id=pad, eos_token_id=eos)
            records = []
            for index, identifier in enumerate(identifiers):
                tail = outputs[index, width:].tolist()
                finish = 'length'
                if eos in tail:
                    tail = tail[:tail.index(eos)+1]
                    finish = 'stop'
                text = tokenizer.decode(tail, skip_special_tokens=True)
                records.append(dict(id=identifier, arm=job['name'], content=text, finish_reason=finish,
                       parsed=parse(text, finish), input_tokens=len(screen_ids[identifier]),
                       prompt_token_sha256=screen_lengths[identifier]['prompt_token_sha256'],
                       adapter_sha256=adapter_sha))
            common.put(path, dict(ids=identifiers, records=records, fingerprint=fingerprint))
            for record in records:
                dest=out/'predictions'/(record['id']+'.json')
                if dest.exists():raise FileExistsError('First inference receipt already exists')
                common.put(dest,record)
            done += len(identifiers)
            del inputs, mask, outputs
        assert done == 160
        common.put(out/'complete.json', dict(N=160, steps=518, consumed=4137,
                   adapter_sha256=adapter_sha, no_shutdown=True, epoch=time.time()))
        progress('complete', 160, 160, 0)
    except BaseException as error:
        save_error = None
        if optimizer is not None and save_current is not None and not updating:
            try:
                if partial and partial_rng is not None:
                    restore_rng(partial_rng)
                optimizer.zero_grad(set_to_none=True)
                save_current()
            except BaseException as problem:
                save_error = repr(problem)
        pointer = common.read(work/'resume.json') if (work/'resume.json').exists() else None
        common.put(out/'failure.json', dict(stage=stage, error_type=type(error).__name__, error=str(error),
                   completed_step=step, saved_step=pointer['step'] if pointer else None,
                   partial_optimizer_update_not_saved=updating, checkpoint_error=save_error,
                   source_pool_2945_preserved=True, additional149_fixed=True, no_shutdown=True, epoch=time.time()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', default='data/full_pool_sft120.json')
    args = parser.parse_args()
    job = common.read(resolve(args.job))
    out = ROOT/'results'/job['name']
    out.mkdir(parents=True, exist_ok=True)
    run(job, out)
