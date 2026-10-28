"""CPU-only archive, SHA and isolated-entry checks; never loads model weights."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import common107 as c
from run107 import verify_bundle

def check(bundle,archive,output=None):
    bundle=Path(bundle);archive=Path(archive)
    manifest=verify_bundle(bundle)
    wanted=dict(manifest['files'], **{'manifest.json':c.sha(bundle/'manifest.json')})
    seen={}
    with tarfile.open(archive,'r:gz') as source:
        for member in source.getmembers():
            name=member.name
            if not member.isfile() or not name.startswith('bundle/') or '..' in Path(name).parts or '\\' in name:
                raise ValueError('Unsafe/nonfile archive member')
            relative=name[len('bundle/'):]
            if relative in seen or relative not in wanted:
                raise ValueError('Unexpected/duplicate archive member')
            h=hashlib.sha256()
            with source.extractfile(member) as stream:
                for part in iter(lambda:stream.read(8*1024*1024),b''):
                    h.update(part)
            if h.hexdigest()!=wanted[relative]:
                raise ValueError('Archive SHA differs: '+relative)
            seen[relative]=member.size
    if set(seen)!=set(wanted):
        raise ValueError('Archive missing a manifest file')
    if any(name.endswith(('.pt','.safetensors','.bin')) or Path(name).name.startswith('.env') for name in seen):
        raise ValueError('Unexpected weight/checkpoint/credential file')
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    task=(bundle/'tasks/107_support_aux').resolve()
    smoke="import sys;sys.path.insert(0,"+repr(str(task))+");import worker107,run107,evaluate107;assert 'torch' not in sys.modules and 'transformers' not in sys.modules;print('isolated_import_ok')"
    with tempfile.TemporaryDirectory(prefix='verifact107_empty_') as empty:
        imported=subprocess.run([sys.executable,'-B','-c',smoke],cwd=empty,env=env,capture_output=True,text=True,check=True)
        for name in ('run107.py','worker107.py','evaluate107.py'):
            subprocess.run([sys.executable,'-B',str(task/name),'--help'],cwd=empty,env=env,capture_output=True,text=True,check=True)
    result=dict(task=107,status='PASS',manifest_sha256=wanted['manifest.json'],archive_sha256=c.sha(archive),
        manifest_files_verified=len(manifest['files']),archive_files_verified=len(seen),archive_file_bytes=sum(seen.values()),
        paths_within_bundle=True,archive_content_SHA_match=True,empty_cwd_import_and_help_exit0=imported.returncode==0,
        PYTHONPATH_cleared=True,torch_transformers_not_imported=True,contains_weights=False,
        contains_clinical_data=True,publishable=False,independent_audit=False,GPU_calls=0,API_calls=0)
    c.put(output or c.OUT/'implementation_package_checks.json',result)
    print(c.canonical(result))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    a=parser.parse_args();check(a.bundle,a.archive,a.output)
