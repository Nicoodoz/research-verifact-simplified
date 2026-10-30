"""Freeze a further development check; no model fitting or new patient access."""
from collections import Counter
from pathlib import Path
import json
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / '.local_models/120_full_pool_sft/internal687'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as c
from data105 import shared
from parse105 import parse
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0, str(ROOT / 'tasks/109_boundary_replay'))
from select109 import load_predictions


def main():
    split = c.read(ROOT / '.local_models/116_research_cycle/data_split.json')
    patients = set(map(str, split['internal_validation_patients']))
    pool = c.rows(ROOT / '.local_models/106_label_preparation/training_pool.jsonl')
    original107 = {r['id'] for r in c.rows(ROOT / '.local_models/105_brief_supervision/train/label_only.jsonl')}
    additional = c.rows(ROOT / '.local_models/117_verdict_probe/lpft_full32_bundle/data/lpft_full32/train.jsonl')
    if len(additional) != 2945 or patients & {str(r['sid']) for r in additional}:
        raise ValueError('The fixed additional-training patient split changed')
    excluded = original107 | {r['id'] for r in additional}
    selected = sorted((r for r in pool if str(r['sid']) in patients and r['id'] not in excluded), key=lambda r: r['id'])
    if len(selected) != 687 or len({r['id'] for r in selected}) != 687 or len(patients) != 8:
        raise ValueError('Expected the complete687 unique non-gradient IDs from the original8 patients')
    B = ROOT / '.local_models/109_boundary_replay/gpu_bundle'
    E = ROOT / '.local_models/109_boundary_replay/gpu_evidence/results'
    meta = {r['id']: r for r in c.rows(B / 'data/pool_metadata.jsonl')}
    caches = []
    for path, ids in ((E / 'mining_a/predictions.jsonl', c.read(B / 'data/stage_a_ids.json')),
                      (E / 'mining_s/predictions.jsonl', c.read(E / 'supported_request.json')['ids'])):
        load_predictions(path, ids, meta)
        caches += c.rows(path)
    by_id = {r['id']: r for r in caches}
    if len(by_id) != len(caches):
        raise ValueError('Duplicate historical first receipt')
    tokenizer = CPUPinnedTokenizer(ROOT / '.local_models/103_lora_selection/models/qwen3.5-9b')
    inputs, keys, prior = [], [], []
    for source in selected:
        i = source['id']
        row = dict(id=i, claim=source['claim'], reference=source['reference'])
        tokens = shared.prompt_ids(tokenizer, row)
        row['expected_prompt_sha256'] = c.digest(c.canonical(tokens))
        if len(tokens) + 384 > 16384:
            raise ValueError('Complete input exceeds the unchanged context allowance: ' + i)
        inputs.append(row)
        keys.append({k: source[k] for k in ('id', 'sid', 'GT', 'author', 'paper_r1')}
                    | dict(input_tokens=len(tokens)))
        if i in by_id:
            old = by_id[i]
            parsed = parse(old['content'], old['finish_reason'])
            if parsed['valid'] != old['parsed']['valid'] or parsed['verdict'] != old['parsed']['verdict']:
                raise ValueError('Historical parser result changed')
            if old['prompt_token_sha256'] != row['expected_prompt_sha256']:
                raise ValueError('Historical107 receipt has another input')
            prior.append(dict(id=i, valid=parsed['valid'], verdict=parsed['verdict'],
                source_adapter_sha256=old['checkpoint_adapter_sha256'],
                source_prompt_sha256_104=old['prompt_token_sha256'], input_tokens=len(tokens)))
    if len(prior) != 69:
        raise ValueError('Expected69 reusable first107 receipts')
    P.mkdir(parents=True, exist_ok=True)
    bundle = P / 'bundle'
    data = bundle / 'data/internal687'
    data.mkdir(parents=True, exist_ok=True)
    c.putl(P / 'keys.jsonl', keys)
    c.putl(P / 'baseline107_cached.jsonl', prior)
    window = c.read(ROOT / '.local_models/CURRENT_RESEARCH.json')['window']
    session = dict(start_epoch=window['start_epoch'], duration_seconds=window['deadline_epoch']-window['start_epoch'],
        GPU_cap_CNY=window['GPU_cap_CNY'], hourly_CNY=window['hourly_CNY'], no_shutdown=True)
    c.frozen(data / 'session.json', (json.dumps(session, indent=2)+'\n').encode())
    done = c.read(ROOT / '.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/training_done.json')
    if (done['steps'], done['consumed']) != (369, 2945):
        raise ValueError('Only the already-retained final120 model is allowed')
    arms = dict(internal107=('/root/autodl-tmp/verifact109/bundle/source107/checkpoint_a',
                            '096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8', {r['id'] for r in prior}),
                internal120=(done['final_checkpoint'], done['adapter_sha256'], set()))
    for name, (checkpoint, sha, complete) in arms.items():
        new = [r for r in inputs if r['id'] not in complete]
        c.frozen(data / (name+'_inputs.jsonl'), ''.join(c.canonical(r)+'\n' for r in new).encode())
        job = dict(name=name, task=120, candidate='internal_development_check',
            model_dir='/root/verifact_image/models/qwen3.5-9b', final_adapter=checkpoint, adapter_sha256=sha,
            inputs_path='data/internal687/'+name+'_inputs.jsonl', session_path='data/internal687/session.json',
            session_sha256=c.sha(data/'session.json'), ids=[r['id'] for r in new], N=len(new),
            max_seq_length=16384, seed=117027, evaluation=dict(batch_size=2, max_new_tokens=384,
                do_sample=False, num_beams=1, repetition_penalty=1., parser='parse105.parse'),
            phase_limit_seconds=2700, save_reserve_seconds=120, no_training=True, no_shutdown=True,
            first_receipts_only=True)
        c.frozen(data / (name+'.json'), (json.dumps(job, indent=2)+'\n').encode())
    files = ['tasks/120_full_pool_sft/run_internal120.py', 'tasks/128_sqrt_weight_refresh/extend128.py',
        'tasks/120_full_pool_sft/analyze120.py', 'tasks/105_brief_supervision/common105.py',
        'tasks/105_brief_supervision/parse105.py', 'tasks/105_brief_supervision/data105.py',
        'tasks/104_supervision_evidence/training104.py']
    for relative in files:
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    with tarfile.open(P / 'bundle120_internal.tar.gz', 'w:gz', compresslevel=1) as archive:
        for file in bundle.rglob('*'):
            if file.is_file():
                archive.add(file, arcname=file.relative_to(bundle), recursive=False)
    summary = dict(N=len(keys), patients=len(patients), GT=dict(Counter(r['GT'] for r in keys)),
        original107_training_IDs_excluded=43, additional120_training_IDs=2945,
        cached107_N=len(prior), new107_N=len(keys)-len(prior), new120_N=len(keys),
        max_input_tokens=max(r['input_tokens'] for r in keys), no_truncation=True,
        no_training=True, no_new_configuration=True, confirmation40_used=False,
        patient_exposure='Original8 validation patients, historically exposed;43 other claims supervised in107.',
        cached_batch_size=1, new_batch_size=2, GPU_started=False)
    c.put(P / 'preparation.json', summary)
    c.put(ROOT / 'outputs/120_full_pool_sft/internal687_preparation.json', summary)
    print(c.canonical(summary))


if __name__ == '__main__':
    main()
