"""Final offline tables/docs check and exact uncommitted review snapshot."""
from pathlib import Path
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import re
import subprocess
import study011 as s
from verify011 import equal_content
from export011 import run as tables
from synthesis011 import run as synthesis

if __name__=='__main__':
    assert not (s.OUT/'handoff_001.json').exists()
    assert not list((s.OUT/'live').rglob('*.lock')) and not (s.OUT/'task_api.lock').exists()
    assert not (s.OUT/'live/main').exists()
    for name in ('verification_001','case_analysis_001','pilot_tables_001','synthesis_001','pilot_analysis_001','offline_003'):s.check(s.OUT/name)
    assert not s.read_json(s.OUT/'pilot_analysis_001/gate.json')['proceed_main']
    old=s.read_json(s.OUT/'readiness_001/history_before_hashes.json')
    assert all(s.pilot.digest_file(s.ROOT/path)==digest for path,digest in old.items())
    docs=[s.ROOT/'README.md',s.ROOT/'AGENTS.md',s.TASK/'README.md',s.OUT/'README.md',s.OUT/'report.md',s.OUT/'audit_handoff.md']
    checked=[]
    for p in docs:
        bb=p.read_bytes();assert not bb.startswith(b'\xef\xbb\xbf');text=bb.decode('utf-8')
        if p.parent==s.ROOT:
            assert b'\n' not in bb.replace(b'\r\n',b'')
            continue
        for target in re.findall(r'\]\(([^\s)]+)\)',text):
            if target.startswith(('http:','https:','#')):continue
            path=target.split('#',1)[0]
            if path.endswith('handoff_001.json'):continue
            assert (p.parent/path).exists(),(p,target)
            checked.append(dict(file=p.relative_to(s.ROOT).as_posix(),target=target))
    out=s.OUT/'final_checks_001';out.mkdir()
    with redirect_stdout(io.StringIO()):
        tables('pilot',out/'tables_replay');synthesis(out/'synthesis_replay')
    count=equal_content(s.OUT/'pilot_tables_001',out/'tables_replay')+equal_content(s.OUT/'synthesis_001',out/'synthesis_replay')
    subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--check'],cwd=s.ROOT,check=True)
    s.pilot.write_json(out/'checks.json',dict(offline=True,new_calls=0,extra_replayed_files=count,history_files_unchanged=len(old),
        documentation_links=len(checked),root_crlf_utf8_preserved=True,main_not_executed=True,independent_audit=False))
    s.pilot.write_json(out/'links.json',checked)
    s.seal(out,[s.OUT/'verification_001/manifest.json'],[Path(__file__),s.TASK/'export011.py',s.TASK/'synthesis011.py'])
    files=docs+[s.ROOT/'tests/test_evidence_integrity_packaging.py']
    files += [p for directory in (s.TASK,s.OUT) for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    hashes={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in sorted(set(files))}
    version=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=s.BASE_HEAD,
        actual_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=s.ROOT,text=True).strip(),
        origin_main=subprocess.check_output(['git','rev-parse','origin/main'],cwd=s.ROOT,text=True).strip(),
        git_status=subprocess.check_output(['git','status','--short'],cwd=s.ROOT,text=True).splitlines(),
        files_sha256=hashes,file_count=len(hashes),execution_complete=True,main_not_executed=True,
        independent_audit=False,paid_execution_stopped=True,history_files_unchanged=len(old),
        snapshot_policy='Exact review bytes; subsequent status/audit docs need not remain equal for ordinary replay. Frozen experiment data and code remain strict.',
        self_excluded='outputs/011_evidence_integrity_packaging/handoff_001.json')
    assert version['actual_head']==s.BASE_HEAD
    s.pilot.write_json(s.OUT/'handoff_001.json',version)
    assert all(s.pilot.digest_file(s.ROOT/path)==digest for path,digest in hashes.items())
    print(s.pilot.canonical(dict(file_count=len(hashes),handoff_sha256=s.pilot.digest_file(s.OUT/'handoff_001.json'),extra_replays=count,head=version['actual_head'],status=version['git_status'])))
