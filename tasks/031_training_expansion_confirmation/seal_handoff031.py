"""Seal executor handoff, preserving older results and avoiding credential disclosure."""
import subprocess
from pathlib import Path
import common031 as c

def run():
    destination=c.OUT/'handoff_001';c.require(not destination.exists(),'Handoff already sealed')
    c.require((c.OUT/'report.md').exists() and (c.OUT/'verification_001/checks.json').exists(),'Finish report and selfcheck first')
    checks={}
    for manifest in ('freeze_001/manifest.json','execution_freeze_001.json','analysis_contract_001.json'):
        for p,h in c.read(c.OUT/manifest)['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Frozen contract changed '+p);checks[p]=h
    for name in ('planning_001','materials_001'):
        manifest=c.read(c.OUT/name/'manifest.json')
        for p,h in manifest['sources'].items():c.require(c.sha(c.ROOT/p)==h,'Historical source changed '+p);checks[p]=h
        for p,h in manifest['outputs'].items():c.require(c.sha(c.OUT/name/p)==h,'Frozen preparation changed '+p);checks[str((c.OUT/name/p).relative_to(c.ROOT))]=h
    c.base.verify_frozen()
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=c.ROOT,text=True).splitlines();allowed={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'}
    c.require(set(changed)<=allowed,'Historical tracked source changed')
    files=sorted(p for root in (c.TASK,c.OUT) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    # Local exact-secret comparison only; never print or persist credentials.
    secrets=[]
    for name in ('.env.siliconflow_pool','.env.aliyun'):
        path=c.ROOT/name
        if path.exists():
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                if '=' in line and 'API_KEY' in line.split('=',1)[0] and not line.lstrip().startswith('#'):
                    v=line.split('=',1)[1].strip().strip('"\'')
                    if len(v)>12:secrets.append(v.encode())
    for p in files:
        data=p.read_bytes();c.require(not any(s in data for s in secrets),'Credential detected in task artifact; do not publish')
    destination.mkdir();c.put(destination/'frozen_dependencies.json',checks)
    c.put(destination/'manifest.json',dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),tracked_changes=changed,new_task_files=len(files),sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in files},navigation_sha256={p:c.sha(c.ROOT/p) for p in sorted(allowed)},historical_contracts_match=True,exact_local_secret_scan_passed=True,independent_audit=False,committed=False,pushed=False))
    print('Executor handoff sealed',len(files),'files; not an independent audit')

if __name__=='__main__':run()
