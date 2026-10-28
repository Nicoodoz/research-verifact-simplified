"""Prepare a minimal PRIVATE runnable107 package. Does not execute GPU work."""
from pathlib import Path
import argparse
import shutil
import tarfile
import common107 as c

DEPENDENCIES = {
    'tasks/104_supervision_evidence': ['training104.py'],
    'tasks/105_brief_supervision': ['common105.py','data105.py','loss105.py','parse105.py','tokenizer_cpu105.py','verify105.py','evaluate105.py'],
    'tasks/107_support_aux': ['common107.py','loss107.py','checkpoint107.py','worker107.py','run107.py','evaluate107.py','cost107.py'],
    'src/verifact_research': ['__init__.py'],
    'src/verifact_research/evaluation': ['__init__.py','core.py','metrics.py'],
}

def validate_config(config):
    old = c.read(c.ROOT/'tasks/105_brief_supervision/config.json')
    if config.get('task') != 107 or config.get('trainable_arms') != list(c.ARMS) or config.get('training_N') != 196:
        raise ValueError('Not the frozen two fresh-arm196 experiment')
    for key in ('model','revision','seed'):
        if config[key] != old[key]:
            raise ValueError('Original base/initialization changed')
    if {k:v for k,v in config['training'].items() if k!='auxiliary'} != old['training']:
        raise ValueError('Original105 main training configuration changed')
    aux = config['training']['auxiliary']
    if aux != dict(type='linear_binary',weight=1.0,positive_label='Supported',representation='prompt_last',head_dtype='float32',head_seed=103028):
        raise ValueError('Unexpected auxiliary configuration')
    batch=config['evaluation']['batch_size']
    if batch not in (1,2):
        raise ValueError('5090 user authorization permits evaluation batch2 or1 only')
    if config['evaluation'] != dict(old['evaluation'],arms=list(c.ARMS),old_predictions_reused=False,batch_size=batch):
        raise ValueError('Original105 inference configuration changed')
    if config['budget']['compute_hard_cap_cny'] != 20 or config['budget']['API_cap_cny'] != 0:
        raise ValueError('Budget changed')

def package(output,receipt=None):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Use a new empty directory, never overwrite a frozen bundle')
    config = c.read(c.TASK/'config.json')
    validate_config(config)
    checks = c.read(c.OUT/'data_checks.json')
    maps = c.read(c.OUT/'tokenizer_summary.json')
    for arm in c.ARMS:
        if c.sha(c.PRIVATE/'train'/(arm+'.jsonl')) != checks['training_sha256']:
            raise ValueError('Frozen training bytes changed')
    if c.sha(c.PRIVATE/'eval_inputs.jsonl') != checks['eval_inputs_sha256']:
        raise ValueError('Frozen evaluation bytes changed')
    for path, expected in maps['input_file_SHA256'].items():
        if c.sha(path) != expected:
            raise ValueError('Tokenized input changed')
    output.mkdir(parents=True,exist_ok=True)
    def copy(source, relative):
        dest = output/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
    for folder, names in DEPENDENCIES.items():
        for name in names:
            copy(c.ROOT/folder/name, folder+'/'+name)
    copy(c.TASK/'config.json','frozen/config.json')
    for name in ('eval_keys.jsonl','train_token_lengths.jsonl','eval_token_lengths.jsonl','eval_batches.json',
                 'tokenizer_summary.json','patient_roles107.json','cost_estimate.json','auxiliary_targets.jsonl'):
        copy(c.OUT/name,'frozen/'+name)
    for name in ('environment_versions.json',):
        copy(c.ROOT/'outputs/105_brief_supervision'/name,'frozen/'+name)
    copy(c.ROOT/'outputs/105_brief_supervision/token_summary.json','frozen/baseline_token_summary.json')
    copy(c.ROOT/'tasks/105_brief_supervision/environment_103_actual.lock','frozen/environment_103_actual.lock')
    c.put(output/'frozen/weights_manifest.json',c.read(c.ROOT/'outputs/103_lora_selection/gpu_weight_sources.json')['qwen3.5-9b'])
    for arm in c.ARMS:
        copy(c.PRIVATE/'train'/(arm+'.jsonl'),'data/train/'+arm+'.jsonl')
    copy(c.PRIVATE/'eval_inputs.jsonl','data/eval_inputs.jsonl')
    c.put(output/'SESSION_REQUIRED.template.json',dict(task=107,user_supplied_rented_instance=True,
        user_request_reference='2026-10-28 user experiment107 staged authorization',
        authorized_at='2026-10-28',hourly_cny=2.88,billing_start_epoch=1793191200,cap_cny=20,API_cap_cny=0,
        fixed_bundle_sha256=None,confirmed_original_9b_environment=False,
        note='User must rent/provide new instance first; operator fills actual quote/start/manifest after verification. No old SSH credential.'))
    c.write(output/'README_HANDOFF.md',
        '# 107 PRIVATE bundle\n\nRestricted original clinical inputs; never publish this package. Contains no base/adapter weights or credentials. '
        'Two fresh original-base training arms, not106 sum/cache design. User has authorized staged107; this package does not rent or start a GPU. '
        'After the user supplies the rented instance, reuse original9B/environment, fill actual session quote/billing start and manifest SHA, run inert preflight then authorized runner. '
        'See tasks/107_support_aux/GPU_HANDOFF.md in the public repository for the full handoff. '
        'GPU checks and whole-run20CNY budget gate must pass before formal optimization. API0. '
        'After all GPU work save adapters/head/checkpoints/raw outputs, then request platform shutdown confirmation; stopping a process does not stop billing. Never release the instance/disk.')
    files = {p.relative_to(output).as_posix():c.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    c.put(output/'manifest.json',dict(task=107,status='CPU_PREPARED_5090_HANDOFF_RECEIVED',files=files,
        clinical_data_private=True,publishable=False,contains_base_weights=False,contains_adapter_weights=False,
        contains_credentials=False,training_N_each=196,epochs=2,optimizer_steps_each=50,
        newly_trained_arms=list(c.ARMS),original105_main_loss_unchanged=True,auxiliary_BCE_weight=1))
    archive = output.parent/(output.name+'.tar.gz')
    if archive.exists():
        raise FileExistsError('Archive exists; preserve frozen bundle')
    temporary = archive.with_name(archive.name+'.tmp')
    with tarfile.open(temporary,'w:gz',compresslevel=6) as tar:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                tar.add(path,arcname='bundle/'+path.relative_to(output).as_posix(),recursive=False)
    temporary.replace(archive)
    report = dict(bundle=str(output),manifest_sha256=c.sha(output/'manifest.json'),files=len(files),
        bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),archive=str(archive),
        archive_sha256=c.sha(archive),archive_bytes=archive.stat().st_size,
        contains_clinical_material=True,publishable=False,contains_base_weights=False,contains_adapter_weights=False,
        no_GPU_or_API=True)
    c.put(receipt or c.OUT/'implementation_package.json',report)
    print(c.canonical(report))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--receipt',type=Path)
    a=parser.parse_args();package(a.output,a.receipt)
