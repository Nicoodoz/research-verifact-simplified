"""CPU preparation of conditional selection-extension and six deployment cases.

No encoder weights/lower23 cache are copied or read. This CLI only prepares
data. Inference helpers require an explicit fair-control continuation decision
and never create an optimizer or select an epoch.
"""
from collections import Counter
from pathlib import Path
import argparse
import shutil
import sys

import common108 as c


def prepare(specification, destination):
    import numpy as np
    spec = c.read(specification)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Use a new extension package directory')
    rows = {row['id']: row for row in c.rows(spec['rows_path'])}
    bags = {row['id']: row for row in c.rows(spec['bags_path'])}
    original500 = c.read(spec['split_path'])['selection']
    roles = c.read(c.ROOT / 'outputs/103_lora_selection/patient_roles.json')['patients']
    allowed = set(map(str, roles['selection']))
    forbidden = set(map(str, roles['confirmation']))
    remaining = [row['id'] for row in rows.values() if row['panel'] == 'selection_remaining']
    if len(remaining) != 1317 or len(original500) != 500:
        raise ValueError('Expected1317 remaining plus the original fixed500 selection cases')
    deployment = []
    selected_patients = set()
    for label in c.LABELS:
        choices = sorted((identifier for identifier in original500 if rows[identifier]['GT'] == label),
                         key=lambda identifier: c.digest('108/deployment6/' + identifier))
        for identifier in choices:
            sid = str(rows[identifier]['sid'])
            if sid in selected_patients:
                continue
            deployment.append(identifier)
            selected_patients.add(sid)
            if sum(rows[item]['GT'] == label for item in deployment) == 2:
                break
        if sum(rows[item]['GT'] == label for item in deployment) != 2:
            raise ValueError('Cannot select two cases per GT from six distinct selection patients')
    identifiers = remaining + deployment
    patients = {str(rows[identifier]['sid']) for identifier in identifiers}
    if not patients <= allowed or patients & forbidden or set(remaining) & set(original500):
        raise ValueError('Selection extension violates authorized patient/ID boundary')
    used = sorted({index for identifier in identifiers for index in bags[identifier]['windows']})
    required = set(used)
    selected_windows = {}
    with (c.ROOT / '.local_models/092/windows.jsonl').open(encoding='utf-8-sig') as stream:
        for index, line in enumerate(stream):
            if index in required:
                selected_windows[index] = __import__('json').loads(line)
    if len(selected_windows) != len(used) or any(len(selected_windows[index]['input_ids']) != 512 for index in used):
        raise ValueError('Original complete512-token windows unavailable')
    lookup = {original: local for local, original in enumerate(used)}
    destination.mkdir(parents=True)
    np.save(destination / 'tokens.npy', np.asarray([selected_windows[index]['input_ids'] for index in used], dtype=np.int32))
    c.putl(destination / 'rows.jsonl', [rows[identifier] for identifier in identifiers])
    c.putl(destination / 'bags.jsonl', [dict(id=identifier, windows=[lookup[index] for index in bags[identifier]['windows']],
             source_windows=bags[identifier]['windows'], reference_sha256=bags[identifier]['reference_sha256'],
             claim_sha256=bags[identifier]['claim_sha256']) for identifier in identifiers])
    c.put(destination / 'splits.json', dict(train=[], validation=[], selection=remaining, deployment=deployment))
    deployment_inputs = []
    sought = set(deployment)
    with (c.ROOT / '.local_models/092/inputs.jsonl').open(encoding='utf-8-sig') as stream:
        for line in stream:
            row = __import__('json').loads(line)
            identifier = row['proposition_id']
            if identifier not in sought:
                continue
            if c.digest(row['text']) != bags[identifier]['claim_sha256'] or c.digest(row['reference']) != bags[identifier]['reference_sha256']:
                raise ValueError('Deployment original claim/C48 differs from frozen092 input')
            deployment_inputs.append(dict(id=identifier, sid=rows[identifier]['sid'], claim=row['text'], reference=row['reference'], source=row['source']))
    if len(deployment_inputs) != 6:
        raise ValueError('Missing original deployment source')
    raw_by = {row['id']: row for row in deployment_inputs}
    c.putl(destination / 'deployment_inputs.jsonl', [raw_by[identifier] for identifier in deployment])
    tokenizer_source = c.ROOT / '.local_models/032/deberta_v3_nli'
    tokenizer_names = ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'added_tokens.json', 'spm.model')
    (destination / 'tokenizer').mkdir()
    for name in tokenizer_names:
        shutil.copyfile(tokenizer_source / name, destination / 'tokenizer' / name)
    # Reuse the actual092 window constructor; this is tokenization preparation,
    # not another model prediction/evaluation or an activation-cache traversal.
    sys.path.insert(0, str(c.ROOT / 'tasks/092_task_adapted_verifier'))
    from cache092 import windows as construct_windows
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(destination / 'tokenizer', local_files_only=True)
    for identifier in deployment:
        row = raw_by[identifier]
        actual, _ = construct_windows(tokenizer, row['claim'], row['reference'], dict(max_length=512, overlap=32))
        expected = [selected_windows[index]['input_ids'] for index in bags[identifier]['windows']]
        if [part['input_ids'] for part in actual] != expected:
            raise ValueError('End-to-end source tokenization does not reproduce original full window bag')
    c.write(destination / 'README.md', '''条件性数据准备包；不是继续评价授权。

selection为原500以外1317条，deployment为原500中按固定hash选出的六例（每GT两例、六患者），不根据本轮预测挑选。
tokens.npy中的窗口为本包局部索引，bags.jsonl的source_windows保存原092全局索引。全部原窗口保留；train/validation为空。
deployment_inputs.jsonl含受限临床原claim与完整C48，仅私有保存；tokenizer目录为原始分词器小文件。

GPU公平对照收益保留且执行者明确决定继续后，先用主包base原始encoder前23层对本包tokens.npy编码独立lower23.npy。
不要拿主包lower23.npy按本包局部索引直接读取。可调用extension108.encode_lower23；需要约manifest.lower23_bytes磁盘。
随后gpu108.Data(Path(extension), lower, torch, numpy, window_microbatch=既有值)直接复用。
net=gpu108.make_adapter(Path(main_bundle), arm, settings, torch)，加载该臂已训练best.pt（strict=True），固定eval。
可调用extension108.predict_fixed分别预测splits.selection与splits.deployment；不再训练、不重选epoch或阈值。
这六例还可从deployment_inputs经原tokenizer与原cache092.windows构造，已在CPU逐token核对与原bag完全一致；端到端计时必须包含分词、前23层、已训练顶部及聚合头，缓存头时间不能冒充完整系统速度。
''')
    files = {path.relative_to(destination).as_posix(): c.sha(path) for path in destination.rglob('*') if path.is_file()}
    summary = dict(task=108, preparation_only=True, selection_remaining=1317, deployment_cases=6,
                   selection_patients=len(patients), deployment_patients=len(selected_patients),
                   remaining_GT=dict(Counter(rows[identifier]['GT'] for identifier in remaining)),
                   remaining_windows=sum(len(bags[identifier]['windows']) for identifier in remaining),
                   deployment_windows=sum(len(bags[identifier]['windows']) for identifier in deployment),
                   windows=len(used), lower23_bytes=len(used) * 512 * 1024 * 2,
                   package_bytes=sum((destination / name).stat().st_size for name in files), files=files,
                   original500_disjoint_from_remaining=True, confirmation40_included=False,
                   deployment_selection='two_per_GT_six_distinct_patients_fixed_hash_without_model_results',
                   deployment_original_tokenization_matches=True, lower23_read_or_hashed=False,
                   large_weights_copied=False, training_or_prediction_executed=False,
                   run_condition='root_explicit_fair_GPU_control_gain_retained_decision')
    c.put(destination / 'manifest.json', summary)
    return {key: value for key, value in summary.items() if key != 'files'}


def encode_lower23(main_bundle, extension, output, decision, cache_batch=8):
    """Inference-only helper; caller owns deadline/budget and output lifecycle."""
    if decision.get('fair_control_gain_retained') is not True:
        raise PermissionError('Explicit retained fair-control benefit decision required')
    import numpy as np
    import torch
    import time
    from transformers import AutoModel
    from gpu108 import check_deadline
    extension = Path(extension)
    if Path(output).exists():
        raise FileExistsError('Preserve existing cache; choose a new extension lower23 output')
    tokens = np.load(extension / 'tokens.npy', mmap_mode='r')
    lower = np.lib.format.open_memmap(output, mode='w+', dtype=np.float16, shape=(len(tokens), 512, 1024))
    encoder = AutoModel.from_pretrained(Path(main_bundle) / 'base', local_files_only=True, torch_dtype=torch.float16).cuda().eval()
    encoder.requires_grad_(False)
    encoder.encoder.layer = torch.nn.ModuleList(list(encoder.encoder.layer)[:23])
    begin = time.perf_counter()
    with torch.inference_mode():
        for start in range(0, len(tokens), cache_batch):
            check_deadline(decision)
            ids = torch.from_numpy(np.array(tokens[start:start + cache_batch], dtype=np.int64)).cuda()
            hidden = encoder(input_ids=ids, attention_mask=torch.ones_like(ids)).last_hidden_state
            lower[start:start + len(ids)] = hidden.cpu().numpy()
            completed = start + len(ids)
            if completed % 256 < cache_batch or completed == len(tokens):
                elapsed = time.perf_counter() - begin
                print(c.canonical(dict(stage='extension_lower23', completed=completed, total=len(tokens),
                                       elapsed_seconds=elapsed, ETA_seconds=(len(tokens) - completed) * elapsed / completed)), flush=True)
    lower.flush()
    del encoder, ids, hidden
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    return lower


def predict_fixed(main_bundle, extension, lower, best_checkpoint, arm, decision, panel='selection', window_microbatch=8):
    if decision.get('fair_control_gain_retained') is not True:
        raise PermissionError('Explicit retained fair-control benefit decision required')
    if arm not in ('flat_ce', 'hier_shared') or panel not in ('selection', 'deployment'):
        raise ValueError('Only fixed fair-control arms and prepared panels allowed')
    import numpy as np
    import torch
    from gpu108 import Data, make_adapter, check_deadline
    check_deadline(decision)
    main_bundle, extension = Path(main_bundle), Path(extension)
    net = make_adapter(main_bundle, arm, c.read(main_bundle / 'settings.json'), torch)
    net.load_state_dict(torch.load(best_checkpoint, map_location='cpu', weights_only=True), strict=True)
    data = Data(extension, lower, torch, np, window_microbatch=window_microbatch)
    probabilities, branches = data.predict(net, data.splits[panel], decision, branches=True)
    result = [dict(id=identifier, sid=data.rows[identifier]['sid'], arm=arm, prediction=c.LABELS[int(probability.argmax())], probabilities=probability.tolist(), branches=branch)
              for identifier, probability, branch in zip(data.splits[panel], probabilities, branches)]
    del net
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    print(c.canonical(prepare(args.data, args.destination)))


if __name__ == '__main__':
    main()
