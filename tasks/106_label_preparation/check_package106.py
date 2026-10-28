"""Local CPU archive/manifest metadata verification; never extracts or loads weights."""
import argparse
import hashlib
from pathlib import Path
import tarfile
import os
import subprocess
import sys
import tempfile
import common106 as c
from run106 import verify_bundle

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    manifest=verify_bundle(a.bundle)
    wanted=dict(manifest['files']);wanted['manifest.json']=c.sha(a.bundle/'manifest.json')
    seen={}
    with tarfile.open(a.archive,'r:gz') as archive:
        for member in archive.getmembers():
            name=member.name
            if not member.isfile() or not name.startswith('bundle/') or '..' in Path(name).parts or '\\' in name:raise ValueError('Unsafe/nonfile archive member')
            relative=name[len('bundle/'):]
            if relative in seen or relative not in wanted:raise ValueError('Unexpected/duplicate archive entry')
            h=hashlib.sha256()
            with archive.extractfile(member) as stream:
                for part in iter(lambda:stream.read(8*1024*1024),b''):h.update(part)
            if h.hexdigest()!=wanted[relative]:raise ValueError('Archive content differs: '+relative)
            seen[relative]=member.size
    if set(seen)!=set(wanted):raise ValueError('Archive missing frozen files')
    control=[name for name in seen if name.endswith('.safetensors')]
    if control!=['control/label_mean/checkpoint_a/adapter_model.safetensors']:raise ValueError('Unexpected physical weights in minimal package')
    if any('35b' in name.lower() or '27b' in name.lower() or Path(name).name.startswith('.env') or name.endswith('training_state.pt') for name in seen):raise ValueError('Nonminimal/private-secret checkpoint asset')
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    task=(a.bundle/'tasks/106_label_preparation').resolve()
    smoke="import sys;sys.path.insert(0,"+repr(str(task))+");import worker106,run106,evaluate106;assert 'torch' not in sys.modules and 'transformers' not in sys.modules;print('isolated_import_ok')"
    with tempfile.TemporaryDirectory(prefix='verifact106_empty_') as empty:
        imported=subprocess.run([sys.executable,'-B','-c',smoke],cwd=empty,env=env,capture_output=True,text=True,check=True)
        helped=subprocess.run([sys.executable,'-B',str(task/'worker106.py'),'--help'],cwd=empty,env=env,capture_output=True,text=True,check=True)
    result=dict(task=106,status='executor_package_checks_passed',manifest_sha256=wanted['manifest.json'],archive_sha256=c.sha(a.archive),
        manifest_files_verified=len(manifest['files']),archive_files_verified=len(seen),archive_file_bytes=sum(seen.values()),
        paths_within_bundle=True,no_symlink_or_path_escape=True,archive_content_SHA_match=True,only_physical_weight_is_frozen_mean_control_adapter=True,
        contains_base_weights=False,contains_control_adapter=True,contains_clinical_data=True,publishable=False,
        empty_cwd_import_and_worker_help_exit0=imported.returncode==helped.returncode==0,empty_cwd_PYTHONPATH_cleared=True,torch_transformers_not_imported=True,
        independent_audit=False,GPU_calls=0,API_calls=0)
    c.put(c.OUT/'implementation_package_checks.json',result);print(c.canonical(result))

if __name__=='__main__':main()
