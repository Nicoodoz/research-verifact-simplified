"""Read-only sync/model checks usable on the next no-GPU instance."""
from pathlib import Path
import argparse
import importlib.metadata as md
import shutil
import common105 as c

def bundle(root):
    root=Path(root);manifest=c.read(root/'manifest.json')
    for name,sha in manifest['files'].items():
        target=(root/name).resolve()
        if not target.is_relative_to(root.resolve()) or c.sha(target)!=sha:raise ValueError('Sync fingerprint mismatch: '+name)
    return manifest

def weights(root,expected):
    root=Path(root)
    if (root/'adapter_config.json').exists():raise ValueError('Original base path contains an adapter')
    if (root/'REVISION').exists() and (root/'REVISION').read_text().strip()!=c.REVISION:raise ValueError('Wrong revision')
    for name,sha in expected['small_file_sha256'].items():
        # Bundle records more upstream small files than 103 remote copied; only
        # necessary runtime files are mandatory; all present files must match.
        path=root/name
        if path.exists():assert c.sha(path)==sha,name
        elif name in {'config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja','model.safetensors.index.json'}:raise FileNotFoundError(path)
    for part in expected['weights']:
        path=root/part['filename']
        if not path.is_file() or path.stat().st_size!=part['bytes'] or c.sha(path)!=part['sha256']:raise ValueError('Original weight shard mismatch: '+part['filename'])
    return dict(revision=c.REVISION,weight_shards=len(expected['weights']),all_weights_SHA_match=True,no_adapter_in_base_path=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--metadata-only',action='store_true')
    a=p.parse_args();bundle(a.bundle)
    a.work.mkdir(parents=True,exist_ok=True)
    free=shutil.disk_usage(a.work).free
    if free<6*1024**3:raise RuntimeError('Need 6 GiB existing free space for rolling checkpoints/results; do not buy disk')
    expected=c.read(a.bundle/'frozen/weights_manifest.json')
    result=weights(a.model_dir,expected) if not a.metadata_only else dict(weight_files_not_checked=True,only_local_preparation=True)
    versions={}
    for name,version in c.read(a.bundle/'frozen/environment_versions.json').items():
        try:actual=md.version(name)
        except md.PackageNotFoundError:actual=None
        versions[name]=dict(expected=version,actual=actual)
    if not a.metadata_only and any(v['actual']!=v['expected'] for v in versions.values()):raise RuntimeError('Reuse exact 103 environment; version mismatch: '+c.canonical(versions))
    if not a.metadata_only:
        # The 103 GPU tokenizer library is 0.23.3, local tokenizer-only is 0.22.2.
        # Do not assume equivalence: verify every real prompt and answer before
        # any GPU work, without loading model weights or requiring a CUDA card.
        import os
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        from transformers import AutoTokenizer
        from data105 import encode,shared
        tok=AutoTokenizer.from_pretrained(str(a.model_dir),trust_remote_code=False,local_files_only=True)
        expected_lengths={(r['arm'],r['id']):r for r in c.rows(a.bundle/'frozen/train_token_lengths.jsonl')}
        for arm in c.ARMS[1:]:
            for row in c.rows(a.bundle/'data/train'/(arm+'.jsonl')):
                encoded=encode(tok,row);wanted=expected_lengths[(arm,row['id'])]
                assert encoded['prompt_token_sha256']==wanted['prompt_token_sha256'] and encoded['answer_sha256']==wanted['answer_sha256']
                assert encoded['verdict_answer_token_indices']==wanted['verdict_answer_token_indices'] and len(encoded['input_ids'])==wanted['total_tokens']
        eval_lengths={r['id']:r for r in c.rows(a.bundle/'frozen/eval_token_lengths.jsonl')}
        for row in c.rows(a.bundle/'data/eval_inputs.jsonl'):
            assert c.digest(c.canonical(shared.prompt_ids(tok,row)))==eval_lengths[row['id']]['prompt_token_sha256']
        result['all_392_train_answer_maps_and_500_eval_prompt_tokens_verified']=True
    result.update(bundle_verified=True,bundle_sha256=c.sha(a.bundle/'manifest.json'),model_dir=str(a.model_dir.resolve()),
                  expected_weights_sha256=c.sha(a.bundle/'frozen/weights_manifest.json'),existing_free_bytes=free,versions=versions,GPU_loaded=False,new_API_calls=0)
    c.put(a.work/'nogpu_preflight.json',result);print(c.canonical(result))

if __name__=='__main__':main()
