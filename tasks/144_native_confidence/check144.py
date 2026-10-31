"""CPU-only source/interface and output-format checks; no model imports."""
from collections import Counter
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import zipfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tasks/113_label_path').is_dir())
PRIVATE = ROOT / '.local_models/parallel_20261031/selective_verification/native_score_preparation'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def formats(paths, batches=False):
    rows = []
    for folder in paths:
        for path in sorted(folder.glob('*.json')):
            if not batches and len(path.stem) != 36:
                continue
            value = read(path)
            rows.extend(value['records'] if batches else [value])
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate native first answers in format check')
    counts = Counter()
    for row in rows:
        content = row.get('content')
        if not isinstance(content, str):
            counts['missing_content'] += 1
        elif content.startswith('{"verdict":"'):
            counts['exact_canonical_prefix'] += 1
        elif re.match(r'^\s*\{\s*"verdict"\s*:\s*"', content):
            counts['whitespace_variant_prefix'] += 1
        else:
            counts['other_format'] += 1
    return dict(N=len(rows), formats=dict(counts), paths=[str(p.relative_to(ROOT)) for p in paths])


def check():
    wheel = ROOT / '.local_models/103_lora_selection/wheelhouse'
    name = 'transformers/models/qwen3_5/modeling_qwen3_5.py'
    with zipfile.ZipFile(wheel / 'transformers-5.17.0-py3-none-any.whl') as package:
        source = package.read(name).decode('utf-8')
    parsed = ast.parse(source)
    classes = {}
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name in ('Qwen3_5ForCausalLM', 'Qwen3_5ForConditionalGeneration'):
            forward = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == 'forward')
            body = ast.get_source_segment(source, forward)
            classes[node.name] = dict(forward_line=forward.lineno,
                explicit_logits_to_keep='logits_to_keep' in [a.arg for a in forward.args.args],
                slices_before_lm_head='self.lm_head(hidden_states[:, slice_indices, :])' in body,
                member_sha256=hashlib.sha256(source.encode()).hexdigest())
    assert len(classes) == 2 and all(x['explicit_logits_to_keep'] and x['slices_before_lm_head'] for x in classes.values())
    with zipfile.ZipFile(wheel / 'unsloth-2026.10.9-py3-none-any.whl') as package:
        vision = package.read('unsloth/models/vision.py').decode('utf-8')
    assert 'elif "logits_to_keep" in keys:' in vision
    cfg = read(ROOT / '.local_models/113_label_path/config.json')
    prefix = [4754, 415, 8217, 3147]
    assert cfg['first_value_index'] == 4 and cfg['branch_ids'] == {'S': 33490, 'Not': 2536}
    assert all(seq[:4] == prefix for seq in cfg['label_sequences'].values())
    result = dict(status='CPU_SOURCE_CHECK_ONLY_NOT_GPU_TESTED',
        versions=dict(transformers='5.17.0', unsloth='2026.10.9', unsloth_zoo='2026.10.9'),
        transformers_member=name, classes=classes, unsloth_explicit_logit_arg_detection=True,
        runtime_guard='Require explicit logits_to_keep on loaded forward; LM-head pre-hook refuses more than one position.',
        prefix=dict(text='{"verdict":"', token_ids=prefix, branch_ids=cfg['branch_ids'],
                    source='113 frozen label_sequences first four tokens; current tokenizer rechecked before model loading'),
        output_formats={
            'native120': formats([ROOT / '.local_models/120_full_pool_sft/resume369/evidence' / n / 'batches'
                                   for n in ('full_pool_sft', 'full_pool_sft_old500', 'full_pool_sft_selection1817')], True),
            'claim_repeat136': formats([ROOT / '.local_models/136_claim_repeat_transfer/evidence' / n / 'claim_repeat'
                                         for n in ('screen160', 'old500', 'full1817')]),
            'relevance_order142': formats([ROOT / '.local_models/142_relevance_order' / n / 'evidence/relevance_order'
                                            for n in ('screen160', 'old500')]),
        }, no_GPU_API_model_import=True,
        interpretation='Scores condition on a forced canonical prefix. Whitespace variants are not the same free-generation token history; never call these full-answer probabilities.')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=PRIVATE / 'interface_check.json')
    args = parser.parse_args()
    value = check()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(value, ensure_ascii=False))


if __name__ == '__main__':
    main()
