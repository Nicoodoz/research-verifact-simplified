"""Verify exact frozen/manifest bytes in Git index before the authorized commit."""
import subprocess
from common087 import *

def main():
    manifest=read(OUT/'delivery_manifest.json');freeze=read(OUT/'freeze.json')
    expected=dict(manifest['contents_sha256']);expected.update(freeze['sources'])
    expected.update({(OUT/name).relative_to(ROOT).as_posix():digest for name,digest in freeze['files'].items()})
    expected[(OUT/'delivery_manifest.json').relative_to(ROOT).as_posix()]=sha(OUT/'delivery_manifest.json')
    paths=list(expected)
    proc=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=''.join(':'+p+'\n' for p in paths).encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    raw=proc.stdout;offset=0
    for p in paths:
        end=raw.index(b'\n',offset);header=raw[offset:end].decode('ascii');parts=header.split()
        assert len(parts)==3 and parts[1]=='blob',p+' missing staged blob'
        size=int(parts[2]);start=end+1;data=raw[start:start+size];offset=start+size+1
        assert hashlib.sha256(data).hexdigest()==expected[p],p+' staged byte mismatch'
    assert offset==len(raw)
    changed=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode('utf-8').split('\0')
    allowed={'.gitattributes','AGENTS.md','README.md','docs/API_POLICY.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md','docs/RESEARCH_EXECUTION.md',
             'docs/087_Codex_F4证据信息干预与紧凑示范验证_执行提示词.md'}
    changed=[p for p in changed if p]
    assert all(p in allowed or p.startswith(('tasks/087_f4_evidence_intervention/','outputs/087_f4_evidence_intervention/')) for p in changed)
    assert '.gitignore' not in changed
    print(canonical(dict(status='PASS',staged_frozen_and_manifest_blobs=len(paths),staged_files=len(changed),unrelated_staged_files=0)))

if __name__=='__main__':main()
