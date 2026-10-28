"""Verify 9B before removing only the two authorized unused clone model dirs."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,socket,subprocess,time

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def put(path,value):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--expected-host',required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--clean-unused',action='store_true');a=p.parse_args()
    actual=socket.gethostname();assert actual==a.expected_host and actual!='autodl-container-19d242bf57-d46bf31e'
    assert actual=='autodl-container-jnb93wme4w-cae1e260','Only the user-designated new clone may be changed'
    a.work.mkdir(parents=True,exist_ok=True)
    mount=Path('/root/autodl-tmp').resolve();base=mount/'verifact103/models';model=base/'qwen3.5-9b'
    assert model.resolve().is_relative_to(mount)
    manifest=json.loads(a.manifest.read_text());before=shutil.disk_usage(mount);started=time.time()
    receipt=dict(hostname=actual,started_epoch=started,mount=str(mount),disk_before=before._asdict(),
        original_instance_connected=False,original_instance_modified=False,required_9B_weight_bytes=sum(x['bytes'] for x in manifest['weights']),
        checked_weights=[],deleted=[])
    put(a.work/'storage_progress.json',receipt)
    assert (model/'REVISION').read_text().strip()==manifest['hf_revision']
    for part in manifest['weights']:
        path=model/part['filename'];assert path.stat().st_size==part['bytes'];actual_sha=sha(path)
        assert actual_sha==part['sha256'],part['filename']
        receipt['checked_weights'].append(dict(filename=part['filename'],sha256=actual_sha,bytes=part['bytes']))
        put(a.work/'storage_progress.json',receipt)
    for name,expected in manifest['small_file_sha256'].items():
        path=model/name
        if path.exists():assert sha(path)==expected,name
    receipt['all_four_9B_shards_match']=True
    receipt['environment_python_exists']=(mount/'verifact103/venv103/bin/python').exists()
    receipt['frozen105_bundle_exists']=(mount/'verifact105/bundle/manifest.json').exists()
    put(a.work/'storage_progress.json',receipt)
    if a.clean_unused:
        for name in ('qwen3.6-35b-a3b','qwen3.8-27b'):
            target=base/name
            assert socket.gethostname()==a.expected_host
            assert not target.is_symlink() and target.resolve().parent==base.resolve() and target.resolve().is_relative_to(mount)
            if not target.exists():continue
            size=int(subprocess.check_output(['du','-sx','-B1',str(target)]).split()[0])
            shutil.rmtree(target)
            receipt['deleted'].append(dict(path=str(target),allocated_bytes=size,new_clone_only=True))
            put(a.work/'storage_progress.json',receipt)
    receipt.update(disk_after=shutil.disk_usage(mount)._asdict(),finished_epoch=time.time(),
        model_redownloaded=False,environment_reinstalled=False,training_started=False)
    put(a.work/'storage_report.json',receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
