"""Prepare a self-contained system-disk image without changing source assets."""
from pathlib import Path
import argparse,glob,hashlib,json,os,shutil,socket,stat,subprocess,sys,time

HOST='autodl-container-19d242bf57-d46bf31e'
DEST=Path('/root/verifact_image')
SOURCE=Path('/root/autodl-tmp/verifact103')
SOURCE_BUNDLE=Path('/root/autodl-tmp/verifact105/bundle')
def read(path):return json.loads(Path(path).read_text())
def put(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def env_entries():
    folder=SOURCE/'venv103';result=[]
    for current,dirs,files in os.walk(folder,followlinks=False):
        parent=Path(current)
        for name in list(dirs):
            path=parent/name
            if path.is_symlink():dirs.remove(name);files.append(name)
        for name in sorted(files):
            path=parent/name;rel=path.relative_to(folder)
            result.append((path,Path('envs/venv103')/rel))
    return result
def entries():
    expected=read(SOURCE_BUNDLE/'frozen/weights_manifest.json');result=[];hashes={}
    names={r['filename'] for r in expected['weights']}|set(expected['small_file_sha256'])|{'REVISION','DOWNLOAD_VERIFIED.json'}
    for name in sorted(names):
        source=SOURCE/'models/qwen3.5-9b'/name
        if not source.exists():
            if name=='DOWNLOAD_VERIFIED.json':continue
            raise FileNotFoundError(source)
        rel=Path('models/qwen3.5-9b')/name;result.append((source,rel))
        if name in expected['small_file_sha256']:hashes[rel.as_posix()]=expected['small_file_sha256'][name]
    for part in expected['weights']:hashes['models/qwen3.5-9b/'+part['filename']]=part['sha256']
    result+=env_entries()
    manifest=read(SOURCE_BUNDLE/'manifest.json')
    assert manifest.get('evaluation_GT_included') is False
    for name in sorted([*manifest['files'],'manifest.json']):
        assert not any(x in name for x in ('eval_keys','eval_manifest','eval_gt'))
        source=SOURCE_BUNDLE/name;rel=Path('105/bundle')/name;result.append((source,rel))
        hashes[rel.as_posix()]=manifest['files'].get(name,sha(source))
    return result,hashes
def link_destination(source):
    raw=os.readlink(source);resolved=source.resolve()
    source_env=SOURCE/'venv103'
    if resolved.is_relative_to(source_env):
        return str(DEST/'envs/venv103'/resolved.relative_to(source_env)) if os.path.isabs(raw) else raw
    if resolved.is_relative_to(Path('/root/autodl-tmp')):raise RuntimeError('External data-disk symlink: '+str(source))
    if not resolved.exists():raise RuntimeError('Broken environment symlink: '+str(source))
    return raw
def plan():
    assert socket.gethostname()==HOST and not glob.glob('/dev/nvidia[0-9]*')
    assert DEST.resolve()==DEST and DEST.stat().st_dev==Path('/').stat().st_dev
    assert DEST.stat().st_dev!=Path('/root/autodl-tmp').stat().st_dev
    items,expected=entries();seen=set();size=0;links=[]
    for source,relative in items:
        info=source.lstat()
        if source.is_symlink():links.append(dict(path=relative.as_posix(),target=link_destination(source)));continue
        assert stat.S_ISREG(info.st_mode),str(source)
        key=(info.st_dev,info.st_ino)
        if key not in seen:size+=info.st_size;seen.add(key)
    usage=shutil.disk_usage(DEST)
    result=dict(epoch=time.time(),destination=str(DEST),system_disk=usage._asdict(),planned_unique_bytes=size,
        planned_file_entries=len(items),unique_regular_files=len(seen),symlinks=links,
        projected_remaining_bytes=usage.free-size,minimum_planned_free_bytes=3*1024**3,
        sufficient=usage.free-size>=3*1024**3,source_assets_retained=True,model_range_files_excluded=True,
        API_calls=0,GPU_loaded=False)
    put(DEST/'metadata/plan.json',result)
    return items,expected,result
def copy_one(source,target):
    before=source.stat();temp=target.with_name(target.name+'.part')
    if temp.exists():raise RuntimeError('Unexpected prior partial file: '+str(temp))
    if shutil.disk_usage(DEST).free-before.st_size<2*1024**3:raise RuntimeError('Preserve2GiB runtime headroom; stop before filling system disk')
    h=hashlib.sha256()
    with source.open('rb') as src,temp.open('xb') as dst:
        for block in iter(lambda:src.read(8*1024*1024),b''):dst.write(block);h.update(block)
        dst.flush()
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Source changed during copy'
    shutil.copystat(source,temp);temp.replace(target)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');a=p.parse_args()
    items,expected,info=plan()
    if not a.build:print(json.dumps(info));return
    if not info['sufficient']:raise RuntimeError('Image assets do not fit; no disk expansion or source cleanup')
    manifest={};hardlinks={};copied=0;last=0
    def progress(stage,which=''):
        put(DEST/'metadata/progress.json',dict(epoch=time.time(),stage=stage,current=which,completed_files=len(manifest),
            copied_bytes=copied,planned_bytes=info['planned_unique_bytes'],free_bytes=shutil.disk_usage(DEST).free))
    progress('copy')
    for source,relative in items:
        target=DEST/relative;assert target.resolve().is_relative_to(DEST)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() or target.is_symlink():raise FileExistsError('Refuse overwrite: '+str(target))
        stat_source=source.lstat()
        if source.is_symlink():
            link=link_destination(source);target.symlink_to(link);manifest[relative.as_posix()]=dict(kind='symlink',target=link)
        else:
            key=(stat_source.st_dev,stat_source.st_ino)
            if key in hardlinks:
                original,digest=hardlinks[key];os.link(original,target)
            else:
                digest=copy_one(source,target);hardlinks[key]=(target,digest);copied+=stat_source.st_size
            if relative.as_posix() in expected:assert digest==expected[relative.as_posix()],str(relative)
            manifest[relative.as_posix()]=dict(kind='file',bytes=stat_source.st_size,sha256=digest)
        if time.time()-last>2:progress('copy',relative.as_posix());last=time.time()
    put(DEST/'metadata/artifacts_manifest.json',dict(created_epoch=time.time(),files=manifest,source_assets_retained=True))
    progress('verify_destination')
    checked=set()
    for name,record in manifest.items():
        path=DEST/name
        if record['kind']=='symlink':assert os.readlink(path)==record['target'] and path.exists();continue
        info_file=path.stat();key=(info_file.st_dev,info_file.st_ino)
        assert info_file.st_dev==DEST.stat().st_dev and info_file.st_size==record['bytes']
        if key not in checked:assert sha(path)==record['sha256'],name;checked.add(key)
        if time.time()-last>2:progress('verify_destination',name);last=time.time()
    progress('environment_and_token_checks')
    py=DEST/'envs/venv103/bin/python';log=(DEST/'metadata/verification.log').open('ab')
    subprocess.run([str(py),'-I','-B',str(DEST/'tools/check_image.py')],check=True,stdout=log,stderr=subprocess.STDOUT)
    subprocess.run([str(py),'-I','-B','-m','pip','check'],check=True,stdout=log,stderr=subprocess.STDOUT)
    log.close()
    final=dict(status='READY_TO_SAVE_IMAGE',finished_epoch=time.time(),root=str(DEST),all_copied_files_SHA_verified=True,
        copied_unique_regular_bytes=copied,manifest_entries=len(manifest),system_disk=shutil.disk_usage(DEST)._asdict(),
        source_assets_unchanged=True,source_and_destination_on_different_mounts=True,API_calls=0,GPU_loaded=False,
        clinical_data_in_private105_bundle=True,evaluation_GT_included=False,autostart_added=False,live_ledger_included=False,
        next='Shutdown original noGPU instance, then save a private system image in AutoDL console')
    put(DEST/'metadata/ready.json',final);progress('READY_TO_SAVE_IMAGE');os.sync();print(json.dumps(final))

if __name__=='__main__':main()
