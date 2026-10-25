"""Final offline delivery checks, including isolated freeze rejection fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import re
import subprocess
import alignment_common as s


def run():
    manifests=sorted(s.OUT.rglob('manifest.json'))
    for m in manifests:
        # The transport manifest has its own receipt validation in io010.stage.
        if m.parent==s.OUT/'live/judge':
            continue
        s.check(m.parent)
    from io010 import stage
    values,attempts=stage('judge')
    assert len(values)==1324 and len(attempts)==1329
    old=s.read_json(s.OUT/'readiness_001/009_before_hashes.json')
    assert all(s.pilot.digest_file(s.ROOT/p)==h for p,h in old.items())
    docs=[s.ROOT/'README.md',s.ROOT/'AGENTS.md',s.TASK/'README.md',
        s.OUT/'README.md',s.OUT/'report.md',s.OUT/'paper_materials.md',s.OUT/'audit_handoff.md']
    links=[]
    for p in docs:
        bb=p.read_bytes();assert not bb.startswith(b'\xef\xbb\xbf')
        text=bb.decode('utf-8')
        if p.parent==s.ROOT:
            assert b'\n' not in bb.replace(b'\r\n',b''),'Root line endings changed'
            continue
        for target in re.findall(r'\]\(([^\s)]+)\)',text):
            if target.startswith(('https:','http:','#')):
                continue
            path=target.split('#',1)[0]
            # The version snapshot is written last; its existence is checked then.
            if path=='handoff_001.json' or path.endswith('/handoff_001.json'):
                continue
            assert (p.parent/path).exists(),(p,target)
            links.append(dict(document=p.relative_to(s.ROOT).as_posix(),target=target))
    rejected=[]
    # Use actual check()/seal(), but modify only disposable synthetic bytes.
    with TemporaryDirectory(prefix='verifact010_freeze_') as temp:
        root=Path(temp).resolve();out=root/'run';out.mkdir()
        data=root/'input.txt';code=root/'compute.py';artifact=out/'prediction.txt'
        data.write_text('frozen input',encoding='utf-8');code.write_text('x=1',encoding='utf-8');artifact.write_text('original prediction',encoding='utf-8')
        with patch.object(s,'ROOT',root):
            s.seal(out,[data],[code]);s.check(out)
            (root/'README.md').write_text('normal changed status',encoding='utf-8')
            (root/'reviews').mkdir();(root/'reviews/README.md').write_text('audit index update',encoding='utf-8')
            s.check(out)
            for name,p in [('input',data),('compute',code),('output',artifact)]:
                before=p.read_bytes();p.write_bytes(before+b' changed')
                try:
                    s.check(out)
                except (ValueError,AssertionError):
                    rejected.append(name)
                finally:
                    p.write_bytes(before)
            s.check(out)
    assert rejected==['input','compute','output']
    # These tracked documents intentionally preserve CRLF under -text attributes.
    # Treat CR as the line terminator; still check real trailing spaces/tabs.
    subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--check'],cwd=s.ROOT,check=True)
    verification=s.read_json(s.OUT/'verification_001/verification.json')
    result=dict(real_frozen_manifests_checked=len(manifests)-1,historical_009_files_unchanged=len(old),
        content_replays=len(verification['replayed_content_sha256']),tests=verification['tests'],
        isolated_mutations_rejected=rejected,mutable_status_and_audit_docs_allowed=True,
        root_encoding_and_crlf_preserved=True,new_local_links_checked=len(links),
        api_calls=0,independent_audit=False,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip())
    out=s.OUT/'final_checks_001';out.mkdir(exist_ok=False)
    s.pilot.write_json(out/'checks.json',result)
    s.pilot.write_json(out/'links.json',links)
    s.seal(out,[s.OUT/'verification_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(result))


if __name__=='__main__':
    run()
