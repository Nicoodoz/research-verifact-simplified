"""Freeze local preparation and build a private minimal no-GPU handoff archive."""
from pathlib import Path
import tarfile
import common105 as c

def main():
    test=c.read(c.OUT/'local_checks.json')
    if test['status']!='PASS':raise ValueError('Finish actual local checks before freezing')
    paths=list(c.TASK.glob('*.py'))+list(c.TASK.glob('*.md'))+list(c.TASK.glob('*.json'))+list(c.TASK.glob('*.lock'))
    names=['train_manifest.jsonl','eval_manifest.jsonl','eval_keys.jsonl','training_plan.json','sample_summary.json',
           'token_summary.json','train_token_lengths.jsonl','eval_token_lengths.jsonl','eval_batches.json',
           'cost_estimate.json','cost_ledger.json','agreement_correction.json','environment_versions.json','local_checks.json']
    paths+=[c.OUT/name for name in names]
    paths+=[c.PRIVATE/'train'/(arm+'.jsonl') for arm in c.ARMS[1:]]
    paths+=[c.PRIVATE/name for name in ('eval_inputs.jsonl','answer_fields.jsonl','source_fingerprints.json')]
    paths+=[c.ROOT/'tasks/104_supervision_evidence/training104.py',c.ROOT/'outputs/104_supervision_evidence/paired_manifest.json',
            c.ROOT/'outputs/103_lora_selection/gpu_weight_sources.json',c.ROOT/'outputs/103_lora_selection/model_metadata.json',
            c.ROOT/'outputs/103_lora_selection/patient_roles.json']
    paths+=[c.ROOT/rel for rel in ('src/verifact_research/__init__.py','src/verifact_research/evaluation/__init__.py','src/verifact_research/evaluation/core.py','src/verifact_research/evaluation/metrics.py')]
    files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(set(paths))}
    freeze_path=c.OUT/'preparation_freeze.json'
    if freeze_path.exists():
        freeze=c.read(freeze_path)
        if freeze['files']!=files:raise ValueError('Preparation differs from frozen version; do not silently replace')
    else:
        c.put(freeze_path,dict(created_utc=c.utc(),files=files,train_N=196,epochs=2,optimizer_steps_per_arm=50,
            samples_consumed_per_arm=392,natural_N=400,pressure_NS=50,pressure_NA=50,new_GPU=0,new_API=0,
            future_predictions_exist=False,minimum_shared_valid_coverage=.95,not_paper_confirmation=True))
    package=c.PRIVATE/('sync_'+c.sha(freeze_path)[:12])/'bundle'
    def copy(source,relative):c.frozen(package/relative,Path(source).read_bytes())
    for path in c.TASK.iterdir():
        if path.is_file() and path.suffix in {'.py','.md','.json','.lock'}:copy(path,'tasks/105_brief_supervision/'+path.name)
    copy(c.ROOT/'tasks/104_supervision_evidence/training104.py','tasks/104_supervision_evidence/training104.py')
    # Small unified evaluation code is included; no dependency wheelhouse.
    for rel in ('src/verifact_research/__init__.py','src/verifact_research/evaluation/__init__.py','src/verifact_research/evaluation/core.py','src/verifact_research/evaluation/metrics.py'):copy(c.ROOT/rel,rel)
    for arm in c.ARMS[1:]:copy(c.PRIVATE/'train'/(arm+'.jsonl'),'data/train/'+arm+'.jsonl')
    copy(c.PRIVATE/'eval_inputs.jsonl','data/eval_inputs.jsonl');copy(c.PRIVATE/'answer_fields.jsonl','data/answer_fields.jsonl')
    for name in ('config.json',):copy(c.TASK/name,'frozen/'+name)
    for name in ('token_summary.json','train_token_lengths.jsonl','eval_token_lengths.jsonl','eval_batches.json','training_plan.json','eval_keys.jsonl','environment_versions.json','cost_estimate.json'):
        copy(c.OUT/name,'frozen/'+name)
    copy(freeze_path,'frozen/preparation_freeze.json')
    weights=c.read(c.ROOT/'outputs/103_lora_selection/gpu_weight_sources.json')['qwen3.5-9b']
    c.frozen(package/'frozen/weights_manifest.json',(c.canonical(weights)+'\n').encode('utf-8'))
    manifests={p.relative_to(package).as_posix():c.sha(p) for p in sorted(package.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    c.frozen(package/'manifest.json',(c.canonical(dict(task=105,files=manifests,base_revision=c.REVISION,contains_private_clinical_data=True,model_weights_included=False,API_credentials_included=False))+'\n').encode('utf-8'))
    archive=c.PRIVATE/'sync105.tar.gz'
    sync_path=c.OUT/'sync_manifest.json'
    if archive.exists():
        old=c.read(sync_path);assert c.sha(archive)==old['archive_sha256'] and old['bundle_manifest_sha256']==c.sha(package/'manifest.json')
    else:
        archive.parent.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
            for path in sorted(package.rglob('*')):
                if path.is_file():tar.add(path,arcname='bundle/'+path.relative_to(package).as_posix(),recursive=False)
        c.put(sync_path,dict(archive='.local_models/105_brief_supervision/sync105.tar.gz',archive_bytes=archive.stat().st_size,
            archive_sha256=c.sha(archive),bundle_manifest_sha256=c.sha(package/'manifest.json'),files=len(manifests)+1,
            local_bundle=package.relative_to(c.ROOT).as_posix(),contains_private_clinical_data=True,
            model_weights_included=False,credentials_included=False,upload_performed=False,cloud_contact=False))
    print(c.canonical(c.read(sync_path)))

if __name__=='__main__':main()
