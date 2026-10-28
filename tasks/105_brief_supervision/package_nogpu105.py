"""Build the minimal v2 runtime; keep v1 freeze/archive and evaluation GT local."""
from pathlib import Path
import shutil,tarfile
import common105 as c

RUNTIME=('common105','data105','loss105','checkpoint105','budget105','worker105',
         'verify105','parse105','tokenizer_cpu105','start_gpu105','run_all105','save105')
FROZEN=('token_summary.json','train_token_lengths.jsonl','eval_token_lengths.jsonl',
        'eval_batches.json','training_plan.json','environment_versions.json','cost_estimate.json')

def main():
    original=c.read(c.OUT/'preparation_freeze.json')
    snapshot=c.PRIVATE/'preparation_v1_snapshot'
    for name,sha in original['files'].items():
        assert c.sha(snapshot/name)==sha,'Missing original preparation snapshot: '+name
    sources={}
    for name in RUNTIME:sources['tasks/105_brief_supervision/'+name+'.py']=c.TASK/(name+'.py')
    for name in ('start105.sh','GPU_HANDOFF.md','protocol.md','config.json'):
        sources['tasks/105_brief_supervision/'+name]=c.TASK/name
    sources['tasks/104_supervision_evidence/training104.py']=c.ROOT/'tasks/104_supervision_evidence/training104.py'
    for arm in c.ARMS[1:]:sources['data/train/'+arm+'.jsonl']=c.PRIVATE/'train'/(arm+'.jsonl')
    sources['data/eval_inputs.jsonl']=c.PRIVATE/'eval_inputs.jsonl'
    for name in FROZEN:sources['frozen/'+name]=c.OUT/name
    sources['frozen/config.json']=c.TASK/'config.json'
    # The private v1 archive contains eval keys. It is retained locally and must
    # never be the cloud handoff for this stage.
    allowed={'id','sid','author','panel','claim','reference','reference_id','reference_sha256'}
    eval_rows=c.rows(c.PRIVATE/'eval_inputs.jsonl')
    assert len(eval_rows)==500 and len({r['id'] for r in eval_rows})==500
    for row in eval_rows:
        assert set(row)<=allowed and {'id','claim','reference'}<=set(row),set(row)
        assert row.get('panel') in {'natural','pressure'}
    for rel,source in sources.items():
        original_rel=source.relative_to(c.ROOT).as_posix()
        if rel.startswith(('data/','frozen/')):assert c.sha(source)==original['files'][original_rel]
    fingerprints={name:c.sha(path) for name,path in sources.items()}
    tag=c.digest(c.canonical(fingerprints))[:12]
    package=c.PRIVATE/('nogpu_'+tag)/'bundle'
    for name,source in sources.items():c.frozen(package/name,source.read_bytes())
    weights=c.read(c.ROOT/'outputs/103_lora_selection/gpu_weight_sources.json')['qwen3.5-9b']
    c.frozen(package/'frozen/weights_manifest.json',(c.canonical(weights)+'\n').encode())
    files={p.relative_to(package).as_posix():c.sha(p) for p in sorted(package.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    c.frozen(package/'manifest.json',(c.canonical(dict(task=105,runtime_version='nogpu_v2',files=files,
        base_revision=c.REVISION,contains_private_clinical_data=True,evaluation_GT_included=False,
        model_weights_included=False,API_credentials_included=False))+'\n').encode())
    archive=c.PRIVATE/('sync_nogpu105_'+tag+'.tar.gz')
    if not archive.exists():
        with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
            for path in sorted(package.rglob('*')):
                if path.is_file():tar.add(path,arcname='bundle/'+path.relative_to(package).as_posix(),recursive=False)
    result=dict(archive=archive.relative_to(c.ROOT).as_posix(),archive_bytes=archive.stat().st_size,
        archive_sha256=c.sha(archive),bundle_manifest_sha256=c.sha(package/'manifest.json'),files=len(files)+1,
        local_bundle=package.relative_to(c.ROOT).as_posix(),contains_private_clinical_data=True,
        evaluation_GT_included=False,model_weights_included=False,credentials_included=False)
    c.put(c.OUT/'sync_nogpu_manifest.json',result)
    changes={name:dict(original_sha256=sha,current_sha256=c.sha(c.ROOT/name)) for name,sha in original['files'].items()
             if c.sha(c.ROOT/name)!=sha}
    c.put(c.OUT/'nogpu_engineering_amendment.json',dict(utc=c.utc(),original_freeze_sha256=c.sha(c.OUT/'preparation_freeze.json'),
        original_sync_archive_sha256=c.sha(c.PRIVATE/'sync105.tar.gz'),original_snapshot_files_verified=len(original['files']),
        changed_original_files=changes,scientific_design_changed=False,train_eval_inputs_answers_changed=False,
        evaluation_GT_cloud=False,reason=['8MiB streaming SHA','tokenizer/Jinja verification without Torch/Transformers',
        'exclude evaluation labels from cloud runtime','single persistent-budget launch/save/shutdown entry',
        'AutoDL shebang-less shutdown shell dispatch and persisted process receipt'],
        current_runtime_manifest_sha256=result['bundle_manifest_sha256']))
    print(c.canonical(result))

if __name__=='__main__':main()
