"""R1/R2 focused checks with isolated bytes/index; no API and no live-file tampering."""
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
import argparse
import hashlib
import io
import json
import os
import socket
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/015_disagreement_adjudication'))
import common014 as c14
import common015 as c15
import verify014
import verify015

def git(args,env):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env,stderr=subprocess.PIPE)

def checkout_check(out):
    """Use HEAD plus the exact intended changes in a disposable index, autocrlf=true."""
    paths=set()
    for folder in (c14.TASK,c15.TASK):
        paths.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(['tests/test_qwen27b_baseline014.py','tests/test_disagreement015.py','tests/test_replay_history014015.py'])
    staged=sorted(paths|{'.gitattributes'})
    # Also test all bound shared execution dependencies against their real HEAD blobs.
    for c in (c14,c15):
        paths.update(c.read(c.OUT/'preparation_001/manifest.json')['execution_code'])
    rows=[]
    with tempfile.TemporaryDirectory(prefix='verifact-checkout-') as temp:
        temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
        git(['read-tree','HEAD'],env)
        git(['-c','core.autocrlf=false','add','--',*staged],env)
        destination=temp/'checkout';destination.mkdir()
        git(['-c','core.autocrlf=true','checkout-index','--prefix='+destination.as_posix()+'/','--',*sorted(paths)],env)
        for name in sorted(paths):
            original=(ROOT/name).read_bytes();new=(destination/name).read_bytes()
            rows.append(dict(path=name,working_sha256=hashlib.sha256(original).hexdigest(),checkout_sha256=hashlib.sha256(new).hexdigest(),same_bytes=original==new))
    result=dict(core_autocrlf=True,isolated_index=True,actual_index_untouched=True,files=len(rows),
        all_bytes_identical=all(r['same_bytes'] for r in rows),checks=rows)
    c14.write_json(out/'checkout.json',result)
    c14.require(result['all_bytes_identical'],'Checkout changed frozen bytes; inspect checkout.json')
    return result

def checks(out):
    c14.require(not out.exists(),'Revision check output exists');out.mkdir(parents=True)
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Revision network blocked')):
        checkout=checkout_check(out)
        original_read=Path.read_bytes
        mutable=['reviews/README.md','reviews/013_multi_mechanism_screen.md',
            'tasks/014_qwen27b_baseline_comparison/README.md','outputs/014_qwen27b_baseline_comparison/README.md','.gitattributes']
        routed={(ROOT/n).resolve():original_read(ROOT/n)+b'\n# isolated normal status update\n' for n in mutable}
        def positive_read(path):return routed.get(path.resolve(),original_read(path))
        positives={}
        with patch.object(Path,'read_bytes',positive_read),redirect_stdout(io.StringIO()):
            for number,module in [('014',verify014),('015',verify015)]:
                target=out/('replay'+number);module.verify(target)
                positives[number]=c14.read(target/'verification.json')
        negatives=[]
        for number,c,module in [('014',c14,verify014),('015',c15,verify015)]:
            cases={
                'input':c.OUT/'preparation_001/jobs.jsonl',
                'receipt':next((c.OUT/'live').glob('receipt_*.json')),
                'computation':c.TASK/('common'+number+'.py'),
                'configuration':c.OUT/'authority_001.json',
                'metrics':c.OUT/'analysis_001/metrics.json',
                'report':c.OUT/'report.md',
            }
            for label,path in cases.items():
                target=path.resolve();changed=original_read(path)+b'\nTAMPERED\n'
                def negative_read(p):return changed if p.resolve()==target else original_read(p)
                try:
                    with patch.object(Path,'read_bytes',negative_read),redirect_stdout(io.StringIO()):
                        module.verify(out/('reject_'+number+'_'+label))
                except (ValueError,AssertionError) as exc:
                    negatives.append(dict(task=number,category=label,path=path.relative_to(ROOT).as_posix(),rejected=True,error=str(exc)))
                else:raise AssertionError('Frozen tampering accepted '+number+' '+label)
        summary=dict(api_calls=0,network_blocked=True,independent_audit=False,
            mutable_update_full_replays={n:dict(tests=v['tests'],tests_passed=v['tests_passed'],
                replayed_content_files=v['replayed_content_files'],history_validation=v['history_validation']) for n,v in positives.items()},
            isolated_document_edits=mutable,frozen_tampering_rejected=negatives,
            windows_checkout_files=checkout['files'],windows_checkout_identical=checkout['all_bytes_identical'])
        c14.write_json(out/'checks.json',summary)
    print(c14.canonical(dict(api_calls=0,positive_full_replays=2,negative_checks=len(negatives),checkout_files=checkout['files'],passed=True)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);checks(p.parse_args().output.resolve())
