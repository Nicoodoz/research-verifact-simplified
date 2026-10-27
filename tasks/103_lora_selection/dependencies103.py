"""Resolve Linux/Python3.12 dependency lock locally without modifying existing envs."""
import urllib.request,json,zipfile,subprocess
import common103 as c
def main():
 with urllib.request.urlopen('https://pypi.org/pypi/uv/json',timeout=45) as r:meta=json.load(r)
 version=meta['info']['version'];f=next(x for x in meta['urls'] if x['filename'].endswith('win_amd64.whl'))
 folder=c.PRIVATE/'tooling';folder.mkdir(parents=True,exist_ok=True);wheel=folder/f['filename']
 if not wheel.exists():urllib.request.urlretrieve(f['url'],wheel)
 assert c.sha(wheel)==f['digests']['sha256']
 with zipfile.ZipFile(wheel) as z:z.extractall(folder/'uv')
 exe=next((folder/'uv').rglob('uv.exe'))
 c.put(c.OUT/'dependency_resolver.json',dict(uv_version=version,wheel_sha256=c.sha(wheel),target='x86_64-manylinux_2_28 / Python3.12',local_environments_modified=False))
 result=subprocess.run([str(exe),'pip','compile',str(c.TASK/'requirements_gpu.in'),'--python-version','3.12','--python-platform','x86_64-manylinux_2_28','--generate-hashes','--output-file',str(c.TASK/'requirements_gpu.lock')],capture_output=True,text=True,encoding='utf-8')
 (folder/'resolve.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 print('resolver_exit',result.returncode,'log',str(folder/'resolve.log'))
 if result.returncode:print(result.stderr[-5000:])
 else:c.put(c.OUT/'dependency_lock.json',dict(utc=c.utc(),status='RESOLVED_NOT_GPU_EXECUTED',sha256=c.sha(c.TASK/'requirements_gpu.lock')))
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
