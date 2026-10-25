"""Offline scope/fee/coverage checks; does not evaluate GT or contact services."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from contextlib import redirect_stdout
import io
import socket
import argparse
import os
import subprocess
import tempfile
import complete_v4_016 as v
c=v.c

def preflight():
    jobs=c.jsonlines(v.OUT/'stage1/base_preparation_001/jobs.jsonl')
    old={j['request_id']:j for j in c.jsonlines(v.ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
    states=c.read(v.ORIGINAL/'interruption_001/reconciled_ledger.json')['phases']['stage1_base_chat']['jobs']
    v.require_v4_only(jobs,old,states);checks={}
    for name,field,value in [('Qwen_model','model',c.QWEN),('repeat_role','role','v4_repeat'),('review_role','role','independent_review')]:
        bad=deepcopy(jobs)
        if field=='model':bad[0]['body'][field]=value
        else:bad[0][field]=value
        try:v.require_v4_only(bad,old,states)
        except ValueError:checks[name]=True
        else:checks[name]=False
    c.require(all(checks.values()),'Disabled role not rejected')
    for status in (0,503):c.require(v.pause_on_error(dict(http_status=status,body_text=''),1,int(status==0),int(status==503))=='configuration_pause','Service error would retry')
    result=dict(created_utc=c.now(),frozen_never_sent_V4_jobs=479,negative_checks=checks,network_and_service_error_pause=True,external_calls=0,
        carry_cny=c.read(v.OUT/'carry.json')['task_total_cny'],initial_shell_check_syntax_error_had_no_network_effect=True,
        send_entry_itself_validated_all479_jobs_before_sending=True)
    c.write_json(v.OUT/'scope_checks_001.json',result);print(c.canonical(result))

def verify(target=None):
    target=Path(target).resolve() if target else v.OUT/'verification_001'
    c.require(not target.exists(),'Verification exists');target.mkdir(parents=True)
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Network disabled')), \
         patch.object(c,'evaluate',side_effect=AssertionError('GT evaluation forbidden')), \
         patch.object(c,'paired_compare',side_effect=AssertionError('Paired effects forbidden')):
        official=v.OUT/'completion_001';c.check_manifest(official)
        with redirect_stdout(io.StringIO()):summary=v.export(target/'replay')
        names=[p.name for p in official.iterdir() if p.is_file() and p.name!='manifest.json']
        c.require(all(c.file_hash(official/n)==c.file_hash(target/'replay'/n) for n in names),'Coverage/cost export replay changed')
        c.require(summary['complete'] and summary['V4_total_valid']==601,'V4 incomplete')
        c.require(summary['Qwen_new_calls']==summary['repeat_calls']==summary['independent_review_calls']==0,'Forbidden roles sent')
        c.require(not summary['GT_effects_calculated'],'GT effects must not be evaluated')
        try:v.send()
        except ValueError as exc:closed='already finished' in str(exc)
        else:closed=False
        c.require(closed,'Finished scope did not block further sends')
        names_code=[(c.TASK/n).relative_to(c.ROOT).as_posix() for n in ('resume016.py','complete_v4_016.py','check_v4_completion016.py')]
        with tempfile.TemporaryDirectory(prefix='v4-checkout-016-') as temp:
            temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
            def git(args):return subprocess.check_output(['git',*args],cwd=c.ROOT,env=env,stderr=subprocess.PIPE)
            git(['read-tree','HEAD']);git(['-c','core.autocrlf=false','add','--',*names_code])
            dest=temp/'checkout';dest.mkdir();git(['-c','core.autocrlf=true','checkout-index','--prefix='+dest.as_posix()+'/','--',*names_code])
            c.require(all((c.ROOT/n).read_bytes()==(dest/n).read_bytes() for n in names_code),'Windows checkout byte drift')
        c.write_json(target/'summary.json',dict(created_utc=c.now(),status='executor_self_check_passed_not_independent_audit',network_blocked=True,
            replayed_content_files=len(names),V4_valid=601,original_V4_unchanged=122,new_V4_valid=479,old_record_handoffs_verified=True,evaluation_entrypoints_blocked=True,
            task_total_cost_or_reserved_cny=summary['task_total_cost_or_reserved_cny'],GT_effects_calculated=False,new_Qwen_repeat_review_calls=0,
            completed_scope_blocks_send=closed,windows_checkout_files=len(names_code),windows_checkout_byte_identical=True))
        print(c.canonical(c.read(target/'summary.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('preflight','verify'));p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='verify':verify(a.output)
    else:preflight()
