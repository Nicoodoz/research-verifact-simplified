"""CPU preparation of conditional120; never connects to a GPU or service."""
from collections import Counter
import argparse
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/120_full_pool_sft'
SOURCE = ROOT / '.local_models/117_verdict_probe/lpft_full32_bundle/data/lpft_full32'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
from data105 import encode, shared, training_plan
from tokenizer_cpu105 import CPUPinnedTokenizer


def prepare():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    source_job = common.read(ROOT / '.local_models/117_verdict_probe/lpft_full32.json')
    originals = common.rows(SOURCE / 'train.jsonl')
    screen = common.rows(SOURCE / 'screen.jsonl')
    validation = common.rows(SOURCE / 'validation.jsonl')
    if len(originals) != 2945 or len({r['id'] for r in originals}) != 2945:
        raise ValueError('Expected the exact119 full32 training list')
    if len({str(r['sid']) for r in originals}) != 32:
        raise ValueError('Expected32 gradient-training patients')
    if {str(r['sid']) for r in originals} & {str(r['sid']) for r in validation}:
        raise ValueError('119 training and internal-validation patients overlap')
    if {r['id'] for r in originals} & {r['id'] for r in screen} or len(screen) != 160:
        raise ValueError('Training and fixed160 evaluation IDs differ from119')
    rows = []
    for source in originals:
        answer = common.canonical({'verdict': source['GT']})
        rows.append(dict(id=source['id'], sid=str(source['sid']), GT=source['GT'],
                         claim=source['claim'], reference=source['reference'],
                         reference_sha256=common.digest(source['reference']),
                         answer=answer, answer_text=answer))
    tokenizer = CPUPinnedTokenizer(ROOT / '.local_models/103_lora_selection/models/qwen3.5-9b')
    lengths = []
    for row, source in zip(rows, originals):
        item = encode(tokenizer, row)
        if item['prompt_token_sha256'] != source['expected_prompt_sha256']:
            raise ValueError('Original119 claim/reference prompt changed: ' + row['id'])
        lengths.append(dict(id=row['id'], prompt_tokens=item['prompt_tokens'],
                            total_tokens=len(item['input_ids']),
                            prompt_token_sha256=item['prompt_token_sha256'],
                            answer_sha256=item['answer_sha256']))
    eval_lengths = []
    for row in screen:
        if {'GT', 'sid', 'panel', 'answer', 'verdict'} & set(row):
            raise ValueError('Screen inputs must remain GT-free')
        ids = shared.prompt_ids(tokenizer, row)
        if common.digest(common.canonical(ids)) != row['expected_prompt_sha256']:
            raise ValueError('Original screen prompt changed: ' + row['id'])
        eval_lengths.append(dict(id=row['id'], prompt_tokens=len(ids),
                                 prompt_token_sha256=row['expected_prompt_sha256']))
    plan = training_plan([r['id'] for r in rows], epochs=1, accumulation=8)
    if len(plan) != 369 or plan[-1]['loss_divisor'] != 1 or plan[-1]['consumed'] != 2945:
        raise ValueError('Unexpected fixed one-pass plan')
    context = 16384
    if max(r['total_tokens'] for r in lengths) > context or max(r['prompt_tokens'] for r in eval_lengths)+384 > context:
        raise ValueError('Complete input exceeds16384; no truncation permitted')
    bundle = PRIVATE / 'bundle'
    data = bundle / 'data/full_pool_sft120'
    data.mkdir(parents=True, exist_ok=True)
    common.putl(data / 'train.jsonl', rows)
    common.putl(data / 'lengths.jsonl', lengths)
    common.putl(data / 'screen.jsonl', screen)
    common.putl(data / 'screen_lengths.jsonl', eval_lengths)
    common.put(data / 'plan.json', plan)
    session = common.read(ROOT / '.local_models/117_verdict_probe/session.json')
    common.put(data / 'session.json', session)
    job = dict(name='full_pool_sft', task=120, candidate='full_pool_sft',
               model_dir=source_job['model_dir'], source107_adapter=source_job['source107_adapter'],
               source_adapter_sha256=source_job['source_adapter_sha256'],
               train_path='data/full_pool_sft120/train.jsonl',
               lengths_path='data/full_pool_sft120/lengths.jsonl',
               plan_path='data/full_pool_sft120/plan.json',
               screen_inputs_path='data/full_pool_sft120/screen.jsonl',
               screen_lengths_path='data/full_pool_sft120/screen_lengths.jsonl',
               session_path='data/full_pool_sft120/session.json', max_seq_length=context,
               seed=117027, phase_limit_seconds=16200, save_reserve_seconds=180,
               expected_seconds_per_example=4.81, expected_screen_seconds=400,
               load_and_gate_reserve_seconds=240,
               training=dict(N=2945, epochs=1, total_steps=369, microbatch=1,
                             gradient_accumulation=8, learning_rate=1e-5,
                             betas=[.9, .999], eps=1e-8, weight_decay=0., gradient_clip=1.,
                             checkpoint_every=16, loss='unchanged loss105.backbone_loss',
                             fresh_Adam=True),
               evaluation=dict(N=160, batch_size=2, max_new_tokens=384,
                               do_sample=False, num_beams=1, repetition_penalty=1.,
                               parser='parse105.parse'),
               checkpoint_selection='fixed final369; no development selection',
               no_shutdown=True, conditional_execution=True)
    common.put(bundle / 'data/full_pool_sft120.json', job)
    common.put(PRIVATE / 'job.json', job)
    modules = ['tasks/120_full_pool_sft/worker120.py', 'tasks/120_full_pool_sft/run120.py',
               'tasks/104_supervision_evidence/training104.py',
               'tasks/105_brief_supervision/common105.py', 'tasks/105_brief_supervision/data105.py',
               'tasks/105_brief_supervision/loss105.py', 'tasks/105_brief_supervision/parse105.py',
               'tasks/107_support_aux/checkpoint107.py']
    for relative in modules:
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    with tarfile.open(PRIVATE / 'bundle120.tar.gz', 'w:gz', compresslevel=1) as archive:
        for path in bundle.rglob('*'):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(bundle), recursive=False)
    source_local = ROOT / '.local_models/109_boundary_replay/source107/checkpoint_a'
    if common.sha(source_local / 'adapter_model.safetensors') != job['source_adapter_sha256']:
        raise ValueError('Local source107 backup differs from the declared source')
    summary = dict(status='PREPARED_CONDITIONAL_NOT_STARTED', task=120,
                   original119_train_sha256=common.sha(SOURCE / 'train.jsonl'),
                   same119_ids_order_GT_claim_reference=True, training_N=len(rows),
                   training_patients=32, GT=dict(Counter(r['GT'] for r in rows)),
                   steps=369, final_tail=1, max_prompt_tokens=max(r['prompt_tokens'] for r in lengths),
                   max_total_tokens=max(r['total_tokens'] for r in lengths),
                   total_training_tokens=sum(r['total_tokens'] for r in lengths),
                   evaluation_N=len(screen), learning_rate=1e-5, fresh_Adam=True,
                   no_new_head=True, no_class_weights=True, no_input_truncation=True,
                   no_new_GPU=True, no_API=True, bundle_bytes=(PRIVATE / 'bundle120.tar.gz').stat().st_size,
                   estimated_train_hours=4.81*len(rows)/3600,
                   original_GPU_gate_still_required=True)
    common.put(PRIVATE / 'preparation.json', summary)
    print(common.canonical(summary))


def self_test():
    """Small CPU checkpoint/short-tail test; no real model or CUDA initialization."""
    import torch
    from safetensors.torch import load_file, save_file
    sys.path.insert(0, str(ROOT / 'tasks/107_support_aux'))
    import checkpoint107 as checkpoint

    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.lora_B = torch.nn.Parameter(torch.tensor([.25]))
        def save_pretrained(self, folder, **_):
            Path(folder).mkdir(parents=True, exist_ok=True)
            save_file(self.state_dict(), str(Path(folder) / 'adapter_model.safetensors'))

    def setup():
        model = Tiny()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=0.)
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.)
        assert not optimizer.state and model.lora_B.item() != 0
        return model, optimizer, scheduler

    toy_plan = training_plan([str(i) for i in range(9)], 1, 8)
    real_plan = training_plan([str(i) for i in range(2945)], 1, 8)
    assert len(real_plan) == 369 and real_plan[-1]['loss_divisor'] == 1
    assert real_plan[-1]['consumed'] == 2945
    def advance(model, optimizer, scheduler, entry):
        optimizer.zero_grad(set_to_none=True)
        for identifier in entry['ids']:
            ((model.lora_B - float(identifier)/10).square().mean()/entry['loss_divisor']).backward()
        optimizer.step()
        scheduler.step()

    control, control_opt, control_sched = setup()
    for entry in toy_plan:
        advance(control, control_opt, control_sched, entry)
    model, optimizer, scheduler = setup()
    advance(model, optimizer, scheduler, toy_plan[0])
    folder = PRIVATE / 'cpu_checkpoint_check'
    fingerprint = dict(task=120, synthetic_CPU_check=True)
    checkpoint.save(model, optimizer, scheduler, folder, 1, 8, fingerprint)
    resumed, resumed_opt, resumed_sched = setup()
    step, consumed, _ = checkpoint.load(resumed_opt, resumed_sched, folder, fingerprint,
        lambda source: resumed.load_state_dict(load_file(str(source / 'adapter_model.safetensors'))))
    assert (step, consumed) == (1, 8)
    advance(resumed, resumed_opt, resumed_sched, toy_plan[step])
    assert torch.equal(control.lora_B, resumed.lora_B)
    assert resumed_opt.param_groups[0]['lr'] == 1e-5
    assert not torch.cuda.is_initialized()
    result = dict(PASS=True, CPU_only=True, plan369=True, final_tail_divisor1=True,
                  source_weight_nonzero_fresh_Adam=True, checkpoint_resume_matches=True,
                  no_CUDA_initialized=True, real_model_loaded=False)
    common.put(PRIVATE / 'cpu_check.json', result)
    print(common.canonical(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else prepare()
