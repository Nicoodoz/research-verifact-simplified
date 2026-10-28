"""Finalize image handoff metadata; no training, API, or shutdown on import."""
from pathlib import Path
import ast,glob,hashlib,json,os,shutil,socket,subprocess,tempfile,time
ROOT=Path('/root/verifact_image')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def put(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def main():
    assert socket.gethostname()=='autodl-container-19d242bf57-d46bf31e' and not glob.glob('/dev/nvidia[0-9]*')
    ready=json.loads((ROOT/'metadata/ready.json').read_text());assert ready['status']=='READY_TO_SAVE_IMAGE'
    checked=json.loads((ROOT/'metadata/environment_token_check.json').read_text());assert checked['status']=='PASS'
    # Exercise only the path helper in an isolated directory, not the original
    # data paths or the top-level restoration program.
    source=(ROOT/'restore105.py').read_text();module=ast.parse(source)
    helper=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='link')
    scope=dict(changes=[])
    exec(compile(ast.Module(body=[helper],type_ignores=[]),'<restore_link_smoke>','exec'),scope)
    cases=[]
    with tempfile.TemporaryDirectory(prefix='restore_smoke_',dir=ROOT/'metadata') as temp:
        base=Path(temp);model=ROOT/'models/qwen3.5-9b'
        fresh=base/'fresh';scope['link'](fresh,model);assert fresh.is_symlink() and fresh.resolve()==model;cases.append('new_path_link')
        scope['link'](fresh,model);cases.append('idempotent_existing_link')
        empty=base/'empty';empty.mkdir();scope['link'](empty,model);assert empty.is_symlink();cases.append('empty_dir_link')
        kept=base/'kept';kept.mkdir();(kept/'marker').write_text('keep');scope['link'](kept,model)
        assert not kept.is_symlink() and (kept/'marker').read_text()=='keep';cases.append('nonempty_dir_preserved')
        wrong=base/'wrong';wrong.symlink_to(ROOT/'metadata',target_is_directory=True)
        try:scope['link'](wrong,model)
        except RuntimeError:cases.append('different_link_refused')
        else:raise AssertionError('Wrong link was accepted')
    for path in [ROOT/'restore105.py',*sorted((ROOT/'tools').glob('*.py'))]:compile(path.read_text(),str(path),'exec')
    smoke=dict(status='PASS',cases=cases,original_data_paths_operated=False,only_helper_executed=True)
    put(ROOT/'metadata/restore_smoke.json',smoke)
    statroot=Path('/').stat().st_dev;assert ROOT.stat().st_dev==statroot and ROOT.stat().st_dev!=Path('/root/autodl-tmp').stat().st_dev
    assert not (ROOT/'105/bundle/frozen/eval_keys.jsonl').exists()
    try:total_root_allocated=int(subprocess.check_output(['du','-sx','-B1','/'],stderr=subprocess.DEVNULL,timeout=18).split()[0])
    except (subprocess.TimeoutExpired,subprocess.CalledProcessError):total_root_allocated=None
    current=time.time();boot=int(next(s.split()[1] for s in Path('/proc/stat').read_text().splitlines() if s.startswith('btime ')))
    ticks=int(Path('/proc/1/stat').read_text().split(') ',1)[1].split()[19]);start=boot+ticks/os.sysconf('SC_CLK_TCK')
    cost=dict(epoch=current,current_nogpu_container_start_proxy_epoch=start,current_nogpu_cny_per_hour=.1,
        current_nogpu_interval_estimate_cny=(current-start)/3600*.1,current_nogpu_interval_includes27Bcleanup_and_image_preparation=True,
        prior_minimum_compute_cny=4.470307342586253,cumulative_known_compute_minimum_cny=4.470307342586253+(current-start)/3600*.1,
        shared_unknown_shutdown_reserve_cny=2,compute_hard_cap_cny=20,GPU_cumulative_hard_limit_minutes=150,
        prior_GPU_seconds_until_shutdown_request=2277.2666959762573,prior_GPU_and_nogpu_platform_endpoints_unconfirmed=True,
        current_interval_end_not_yet_observed=True,actual_platform_invoice_observed=False,API_calls=0,ledger_reset=False)
    put(ROOT/'105/cost_checkpoint/image_preparation_cost.json',cost)
    extras=[ROOT/'restore105.py',ROOT/'README_IMAGE.md',ROOT/'105/environment_103_actual.lock']
    extras+=sorted((ROOT/'tools').glob('*.py'))+sorted((ROOT/'105/cost_checkpoint').glob('*'))
    extras+= [ROOT/'metadata/plan.json',ROOT/'metadata/artifacts_manifest.json',ROOT/'metadata/environment_token_check.json',ROOT/'metadata/restore_smoke.json',ROOT/'metadata/ready.json']
    hashes={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in extras if p.is_file()}
    total=json.loads((ROOT/'metadata/artifacts_manifest.json').read_text())['files']
    kinds={'models':0,'environment':0,'frozen105':0}
    for name,record in total.items():
        if record['kind']!='file':continue
        key='models' if name.startswith('models/') else 'environment' if name.startswith('envs/') else 'frozen105'
        kinds[key]+=record['bytes']
    result=dict(status='READY_TO_SAVE_PRIVATE_IMAGE',epoch=current,hostname=socket.gethostname(),system_disk_root=str(ROOT),
        original_data_disk_assets_retained=True,system_disk=shutil.disk_usage(ROOT)._asdict(),whole_system_allocated_bytes=total_root_allocated,
        component_file_bytes=kinds,artifact_entries=len(total),all_asset_source_destination_SHA_match=True,
        copied_env_prefix_verified=True,train_answer_maps_verified=checked['train_answers_verified'],eval_prompt_tokens_verified=checked['eval_prompts_verified'],
        restoration_helper_smoke=smoke['status'],credentials_copied_into_package=False,clinical_inputs_included=True,evaluation_GT_included=False,
        live_ledger_or_autostart_added=False,GPU_loaded=False,API_calls=0,supplemental_hashes=hashes,
        current_nogpu_compute_estimate=cost,next_command='/root/miniconda3/bin/python -B /root/verifact_image/restore105.py',
        console_action_after_shutdown='Save private system image; keep instance and disk')
    put(ROOT/'metadata/image_delivery.json',result);os.sync();print(json.dumps(result))

if __name__=='__main__':main()
