"""Write one immutable review snapshot after all execution work has stopped."""
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import alignment_common as s


if __name__=='__main__':
    target=s.OUT/'handoff_001.json'
    assert not target.exists()
    assert not list((s.OUT/'live').rglob('*.lock'))
    for name in ('verification_001','final_checks_001'):
        s.check(s.OUT/name)
    prior=s.read_json(s.OUT/'readiness_001/009_before_hashes.json')
    assert all(s.pilot.digest_file(s.ROOT/name)==h for name,h in prior.items())
    fixed=[s.ROOT/'README.md',s.ROOT/'AGENTS.md',s.ROOT/'tests/test_baseline_alignment.py']
    files=sorted(set(fixed+[p for directory in (s.TASK,s.OUT) for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts]))
    hashes={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in files}
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        base_head=s.BASE_HEAD,actual_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=s.ROOT,text=True).strip(),
        origin_main=subprocess.check_output(['git','rev-parse','origin/main'],cwd=s.ROOT,text=True).strip(),
        git_status=subprocess.check_output(['git','status','--short'],cwd=s.ROOT,text=True).splitlines(),
        files_sha256=hashes,file_count=len(hashes),historical_009_files_unchanged=len(prior),
        independent_audit=False,execution_complete=True,paid_execution_stopped=True,
        mutable_document_policy='This is the exact review snapshot. Future README/AGENTS/audit updates do not block ordinary receipt replay; frozen experiment materials remain strict.',
        self_excluded=target.relative_to(s.ROOT).as_posix())
    assert result['actual_head']==s.BASE_HEAD
    s.pilot.write_json(target,result)
    assert all(s.pilot.digest_file(s.ROOT/name)==h for name,h in hashes.items())
    print(s.pilot.canonical(dict(files=len(hashes),head=result['actual_head'],handoff_sha256=s.pilot.digest_file(target),status=result['git_status'])))
