"""Build only the minimal private 9B experiment package; never execute it."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import sys
import tarfile
import common106 as c

DEPENDENCIES={
 'tasks/104_supervision_evidence':['training104.py'],
 'tasks/105_brief_supervision':['common105.py','data105.py','loss105.py','checkpoint105.py','parse105.py','tokenizer_cpu105.py','verify105.py','evaluate105.py'],
 'tasks/106_label_preparation':['common106.py','objectives106.py','tokenizer106.py','worker106.py','run106.py','evaluate106.py','loss106.py'],
 'src/verifact_research':['__init__.py'],
 'src/verifact_research/evaluation':['__init__.py','core.py','metrics.py'],
}

def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)

def package(output,config,data_dir):
    output=Path(output).resolve();config=Path(config);data_dir=Path(data_dir)
    if output.exists() and any(output.iterdir()):raise FileExistsError('Use a new empty package directory; do not overwrite a frozen bundle')
    output.mkdir(parents=True,exist_ok=True)
    old=c.read(c.ROOT/'tasks/105_brief_supervision/config.json');new=c.read(config)
    if any(new.get(key)!=old[key] for key in ('model','revision','seed')):raise ValueError('Unexpected model/revision/seed change')
    for key,value in old['training'].items():
        if key not in {'order'} and new['training'].get(key)!=value:raise ValueError('Unexpected training-objective/setting change: '+key)
    for key,value in old['evaluation'].items():
        if key not in {'arms','old_predictions_reused'} and new['evaluation'].get(key)!=value:raise ValueError('Unexpected generation/evaluation setting change: '+key)
    if new.get('training_N')!=196 or new.get('trainable_arms')!=['label_sum'] or new['training'].get('value_token_mean_normalizer')!=360/196:raise ValueError('Wrong fixed196 objective contrast')
    if new['training'].get('candidate_loss')!='verdict_value_sum_CE_div_fixed_global_mean_length_plus_other_answer_mean_CE':raise ValueError('Unexpected candidate objective')
    maps=c.read(c.OUT/'tokenizer_summary.json')
    source_hashes={Path(name).name:value for name,value in maps['input_file_SHA256'].items()}
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
    allowed=set(map(str,roles['train']));selection=set(map(str,roles['selection']))
    if allowed & selection:raise ValueError('Training/selection patient roles overlap')
    for arm in c.ARMS:
        if c.sha(data_dir/(arm+'.jsonl'))!=source_hashes[arm+'.jsonl']:raise ValueError('Training data changed after tokenization')
        if any(str(r['sid']) not in allowed for r in c.rows(data_dir/(arm+'.jsonl'))):raise ValueError('Non-training patient in training data')
        if c.sha(data_dir/(arm+'.jsonl'))!=c.sha(c.ROOT/'.local_models/105_brief_supervision/train/label_only.jsonl'):raise ValueError('The objective contrast must use exact frozen105 mean training data/order')
    if c.sha(c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')!=source_hashes['eval_inputs.jsonl']:raise ValueError('Evaluation input changed after tokenization')
    if any(str(r['sid']) not in selection for r in c.rows(c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')):raise ValueError('Non-selection patient in development inputs')
    # Explicit allowlist: task code, frozen clinical inputs and ONE control
    # adapter. No key/env, original base weights or unrelated task histories.
    for folder,names in DEPENDENCIES.items():
        for name in names:copy(c.ROOT/folder/name,output/folder/name)
    copy(config,output/'frozen/config.json')
    copy(c.OUT/'cost_estimate.json',output/'frozen/cost_estimate.json')
    c.put(output/'frozen/patient_roles106.json',dict(train=sorted(allowed),selection=sorted(selection),all100_historically_exposed=True,
          confirmation_content_labels_predictions_not_used=True,source_sha256=c.sha(c.ROOT/'outputs/103_lora_selection/patient_roles.json')))
    for arm in c.ARMS:copy(data_dir/(arm+'.jsonl'),output/'data/train'/(arm+'.jsonl'))
    control=c.ROOT/'.local_models/105_brief_supervision/a800/backup/label_only'
    control_meta=c.read(control/'critical_backup_verified.json')
    if control_meta['step']!=50 or control_meta['consumed']!=392:raise ValueError('Wrong105 mean control training state')
    for name,sha in control_meta['files'].items():
        source=control/'checkpoint_a'/name
        if c.sha(source)!=sha:raise ValueError('Mean adapter SHA mismatch')
        copy(source,output/'control/label_mean/checkpoint_a'/name)
    c.put(output/'frozen/mean_control_adapter.json',dict(control_meta,source_task=105,source_arm='label_only',
          never_candidate_initialization=True,training_data_sha256=c.sha(data_dir/'label_mean.jsonl')))
    copy(data_dir/'diagnostic_inputs.jsonl',output/'data/diagnostic_inputs.jsonl')
    copy(c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl',output/'data/eval_inputs.jsonl')
    copy(c.ROOT/'outputs/105_brief_supervision/eval_keys.jsonl',output/'frozen/eval_keys.jsonl')
    for name in ('train_token_lengths.jsonl','eval_token_lengths.jsonl','diagnostic_token_lengths.jsonl','eval_batches.json','diagnostic_batches.json','diagnostic_manifest.jsonl','tokenizer_summary.json','tokenizer_labels.json'):
        copy(c.OUT/name,output/'frozen'/name)
    for name in ('environment_versions.json',):
        copy(c.ROOT/'outputs/105_brief_supervision'/name,output/'frozen'/name)
    c.put(output/'frozen/weights_manifest.json',c.read(c.ROOT/'outputs/103_lora_selection/gpu_weight_sources.json')['qwen3.5-9b'])
    copy(c.ROOT/'outputs/105_brief_supervision/token_summary.json',output/'frozen/baseline_token_summary.json')
    loads=c.rows(c.ROOT/'.local_models/105_brief_supervision/a800/evidence/results/loads.jsonl')
    names={r['gpu'] for r in loads}
    if len(names)!=1:raise ValueError('Ambiguous105 GPU runtime record')
    c.put(output/'frozen/expected_runtime105.json',dict(GPU_name=next(iter(names)),context_tokens=c.read(c.ROOT/'outputs/105_brief_supervision/token_summary.json')['required_context_tokens'],
          dtype='BF16',quantization=False,CPU_offload=False,backend='105 pinned Unsloth/Transformers versions',
          source_loads_sha256=c.sha(c.ROOT/'.local_models/105_brief_supervision/a800/evidence/results/loads.jsonl'),
          cache_reuse_requires_exact_GPU_name_and_all_pinned_versions=True))
    copy(c.ROOT/'tasks/105_brief_supervision/environment_103_actual.lock',output/'frozen/environment_103_actual.lock')
    # Baseline reuse is read-only and conditional on all input token hashes and
    # batch assignments matching. Bad first answers remain invalid, not rerun.
    old_lengths={r['id']:r for r in c.rows(c.ROOT/'outputs/105_brief_supervision/eval_token_lengths.jsonl')}
    current=c.rows(c.OUT/'eval_token_lengths.jsonl')
    if len(current)!=500 or any(r['prompt_token_sha256']!=old_lengths[r['id']]['prompt_token_sha256'] for r in current):raise ValueError('Base cache input mismatch')
    old_batches=c.read(c.ROOT/'outputs/105_brief_supervision/eval_batches.json')
    if c.read(c.OUT/'eval_batches.json')['batches']!=old_batches['batches']:raise ValueError('Base cache batch composition mismatch')
    baseline=[r for r in c.rows(c.ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r.get('arm')=='base_judge']
    if len(baseline)!=500:raise ValueError('Missing original base baseline')
    c.putl(output/'frozen/base_judge_cached.jsonl',baseline)
    historical=[r for r in c.rows(c.ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r.get('arm')=='label_only']
    if len(historical)!=500 or any(not r['parsed']['valid'] for r in historical):raise ValueError('Historical105 label-only quality anchor incomplete')
    c.putl(output/'frozen/105_label_only_cached.jsonl',historical)
    c.putl(output/'frozen/label_mean_cached.jsonl',[dict(r,arm='label_mean',source_task105_arm='label_only') for r in historical])
    c.put(output/'frozen/base_cache_provenance.json',dict(source='105/base_judge',source_predictions_sha256=c.sha(c.ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl'),
          original_prompt_module_sha256=c.sha(c.ROOT/'tasks/104_supervision_evidence/training104.py'),same_original_revision=c.REVISION,
          all500_prompt_token_SHA_match=True,batch_composition_identical=True,parser_sha256=c.sha(c.ROOT/'tasks/105_brief_supervision/parse105.py'),
          generation='greedy BF16 thinking_off batch8 max_new_tokens384 no_retry',invalid_first_answers_retained=True,
          context_length_note='Development evaluation reloads using original105 context bound; training/diagnostics may require longer bound. Future GPU identity and pinned environment must match'))
    template=dict(task=106,explicit_user_gpu_authorization=False,user_request_reference=None,authorized_at=None,hourly_cny=None,
                  billing_start_epoch=None,cap_cny=None,fixed_bundle_sha256=None,confirmed_original_9b_environment=False,baseline_cache_mode=None,
                  accept_cross_hardware_training_diagnostic_only=False)
    c.put(output/'AUTHORIZATION_REQUIRED.template.json',template)
    c.write(output/'README_HANDOFF.md',
        '# 106 minimal private package\n\nPreparation only: no GPU authorization is included. This PRIVATE package contains restricted clinical training/evaluation inputs and the173MB frozen mean control adapter. It must not be published. Original base weights and credentials are not included.\n\n'
        'Reuse the pinned original Qwen3.5-9B base and actual 103/105 environment. Do not clone 27B/35B, download new weights, or supply an adapter as base.\n\n'
        '1. On a no-card instance, run `python tasks/106_label_preparation/run106.py preflight --bundle . --model-dir <original9b> --work <results>`. This verifies all shards, versions and every real token map; it imports no torch.\n'
        '2. Obtain a NEW explicit user GPU decision, actual quote/start and budget. Fill a private authorization record bound to manifest.json SHA. The supplied template is deliberately unauthorized.\n'
        '3. Record baseline_cache_mode=reuse only for exact NVIDIA A800-SXM4-80GB and pinned105 environment/context/dtype/batches. A different GPU or backend requires mode=rerun and a NEW base500 plus frozen-mean-adapter500 evaluation budget (105 observed19.72+6.94 generation minutes, plus loading/preflight margin); do not silently claim strict cache comparability. Only after that decision run `python tasks/106_label_preparation/run106.py run --bundle . --model-dir <original9b> --work <results> --authorization <user-authorized.json> --execute-authorized-gpu`.\n'
        '4. The resource gate, base/mean training diagnostics, ONE fresh-base label_sum196x2 training, sum development500 and sum diagnostics run serially. Frozen105 label_mean adapter and both old development500 caches are reused only if conditions match. Rerun mode evaluates base500 and frozen mean-adapter500; it never retrains mean. Complete stages/answers are retained.\n'
        '5. Save final adapters and small raw outputs, then manually stop the instance in the platform. MANUAL_SHUTDOWN_REQUIRED.json is a reminder, not proof billing stopped. Transfer/report on CPU afterwards. Never share clinical files, API keys or weights publicly.\n\n'
        'The only active change is verdict-value loss: label_mean token mean versus label_sum full value-token sum divided by fixed global360/196; other-answer mean stays1. Same original196 data/order, prompt, label interface, 2epochs and decoding. The512 candidate data assets are not active in this package.\n\n'
        'Different-GPU rerun aligns INFERENCE hardware only; frozen mean TRAINING remains105 A800. Such a run requires explicit accept_cross_hardware_training_diagnostic_only=true and is marked non_strict_training_hardware_comparison. A strict new-GPU loss-only comparison would require a separately frozen new mean training, which this package never adds. Backend versions stay hard-locked even in rerun mode.\n')
    for arm in c.ARMS:
        if c.sha(output/'data/train'/(arm+'.jsonl'))!=source_hashes[arm+'.jsonl']:raise ValueError('Copied data/token map mismatch')
    files={p.relative_to(output).as_posix():c.sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    manifest=dict(task=106,status='PREPARATION_ONLY_REQUIRES_NEW_GPU_DECISION',files=files,clinical_data_private=True,contains_weights=True,
                  contains_base_weights=False,contains_control_adapter=True,contains_credentials=False,publishable=False,
                  candidate_fresh_base_initialization=True,control_is_frozen105_mean_adapter=True,training_N_each=196,epochs=2,optimizer_steps_each=50,
                  newly_trained_arms=['label_sum'],fixed_value_sum_divisor=360/196)
    c.put(output/'manifest.json',manifest)
    archive=output.parent/(output.name+'.tar.gz')
    if archive.exists():raise FileExistsError('Do not overwrite an existing handoff archive')
    temporary=archive.with_name(archive.name+'.tmp')
    with tarfile.open(temporary,'w:gz',compresslevel=6) as tar:
        for path in sorted(output.rglob('*')):
            if path.is_file():tar.add(path,arcname='bundle/'+path.relative_to(output).as_posix(),recursive=False)
    temporary.replace(archive)
    report=dict(bundle=str(output),manifest_sha256=c.sha(output/'manifest.json'),files=len(files),bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
                archive=str(archive),archive_sha256=c.sha(archive),archive_bytes=archive.stat().st_size,
                no_GPU_or_API=True,contains_clinical_material=True,publishable=False)
    c.put(c.OUT/'implementation_package.json',report);print(c.canonical(report));return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--config',type=Path,default=c.TASK/'config.json');p.add_argument('--data-dir',type=Path,default=c.PRIVATE)
    a=p.parse_args();package(a.output,a.config,a.data_dir)

if __name__=='__main__':main()
