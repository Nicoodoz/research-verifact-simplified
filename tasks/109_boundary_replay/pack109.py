"""CPU packaging of109 data/current107 source; never downloads weights or usesGPU."""
from pathlib import Path
import argparse,os,shutil,tarfile
import common109 as c

def copy(src,dst):
    src=Path(src);dst=Path(dst);dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        if not dst.resolve().is_relative_to(c.PRIVATE.resolve()):raise ValueError('Only replace our private packaging files')
        dst.unlink()
    # Link only our immutable private tensor copies. Source-code edits must not
    # mutate a previously frozen bundle through a hard link.
    if src.suffix in {'.pt','.safetensors'} and src.resolve().is_relative_to((c.PRIVATE/'source107').resolve()):
        try:os.link(src,dst)
        except OSError:shutil.copyfile(src,dst)
    else:shutil.copyfile(src,dst)

def prepare():
    bundle=c.PRIVATE/'gpu_bundle';bundle.mkdir(parents=True,exist_ok=True)
    for folder in ('data','source107','frozen'):
        for src in (c.PRIVATE/folder).rglob('*'):
            if src.is_file():copy(src,bundle/src.relative_to(c.PRIVATE))
    for src in c.TASK.glob('*'):
        if src.is_file() and src.suffix in {'.py','.json','.md'} and src.name!='CURRENT.md':copy(src,bundle/src.relative_to(c.ROOT))
    old_current=bundle/'tasks/109_boundary_replay/CURRENT.md'
    if old_current.is_file() and old_current.resolve().is_relative_to(bundle.resolve()):old_current.unlink()
    dependencies={
        '104_supervision_evidence':['training104.py'],
        '105_brief_supervision':['common105.py','data105.py','loss105.py','parse105.py','tokenizer_cpu105.py'],
        '107_support_aux':['checkpoint107.py']}
    for task,names in dependencies.items():
        for name in names:copy(c.ROOT/'tasks'/task/name,bundle/'tasks'/task/name)
    for name in ('__init__.py','evaluation/__init__.py','evaluation/core.py','evaluation/metrics.py'):
        copy(c.ROOT/'src/verifact_research'/name,bundle/'src/verifact_research'/name)
    old=c.ROOT/'.local_models/107_support_aux/gpu_bundle_5090_run/frozen/config.json'
    copy(old,bundle/'frozen/source107_config.json');copy(c.TASK/'config.json',bundle/'frozen/config109.json')
    assets=c.read(c.ROOT/'outputs/107_support_aux/5090_assets_verification.json')
    c.put(bundle/'frozen/model_assets.json',dict(model=assets['model'],revision=assets['revision'],files=assets['files'],versions=assets['versions'],
        large_weight_SHAs_from_actual107_record=True,not_new_remote_verification=True))
    copy(c.ROOT/'outputs/107_support_aux/train_manifest.jsonl',bundle/'frozen/source107_train_manifest.jsonl')
    # No credentials in the template; filling it is only allowed after a NEW user rental/authorization.
    c.put(bundle/'SESSION_REQUIRED.template.json',dict(task=109,GPU_execution_authorized=False,user_supplied_rented_instance=False,
        authorization_reference='FILL_FROM_NEW_USER_GPU_AUTHORIZATION_NOT_CPU_PREPARATION',bound_instance='FILL_NEW_INSTANCE',
        hourly_cny=None,billing_start_epoch=None,cap_cny=None,shutdown_reserve_cny=1,prior_GPU_cny=0,
        fixed_bundle_sha256='FILL_AFTER_RENTAL_FROM_THIS_MANIFEST',API_cap_cny=0,platform_deadline_epoch=None))
    source=c.read(bundle/'source107/resume.json');complete=c.read(bundle/'source107'/source['slot']/'checkpoint_complete.json')
    hashes={'source107/'+source['slot']+'/'+n:h for n,h in complete['files'].items()}
    hashes['source107/'+source['slot']+'/checkpoint_complete.json']=source['complete_sha256']
    files={}
    for path in sorted(bundle.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            name=path.relative_to(bundle).as_posix();files[name]=dict(bytes=path.stat().st_size,sha256=hashes.get(name) or c.sha(path))
    manifest=dict(task=109,name='boundary_replay',preparation_only=True,source107_final_label_only=True,
        files=files,package_bytes=sum(v['bytes'] for v in files.values()),contains_credentials=False,
        contains_private_clinical_text=True,contains_original9B_base_weights=False,
        model_training_or_inference_executed=False,actual_hard_examples_selected=False)
    c.put(bundle/'manifest.json',manifest)
    archive=c.PRIVATE/'boundary_replay109.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():tar.add(path,arcname='bundle/'+path.relative_to(bundle).as_posix(),recursive=False)
    receipt=dict(task=109,private_archive=str(archive.relative_to(c.ROOT)).replace('\\','/'),archive_bytes=archive.stat().st_size,
        bundle_manifest_sha256=c.sha(bundle/'manifest.json'),unpacked_bytes=manifest['package_bytes'],files=len(files),
        private_only=True,base_weights_included=False,new_GPU_calls=0,new_paid_API_cny=0,
        reused107_checkpoint_hash_receipt_not_rehashed_for_each_copy=True)
    c.put(c.OUT/'package_summary.json',receipt);print(c.canonical(receipt))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args();prepare()
