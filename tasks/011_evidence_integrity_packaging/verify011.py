"""Network-blocked 011 replay. Historical drafts retain their original code bytes."""
from pathlib import Path
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
import argparse
import io
import unittest
import subprocess
import study011 as s
from prepare011 import prepare
from score011 import score
from diagnose_inputs011 import run as diagnose
from diagnose_context011 import run as diagnose_context

def equal_content(original,replay):
    count=0
    for p in original.rglob('*'):
        if p.is_file() and p.name!='manifest.json':
            other=replay/p.relative_to(original)
            assert p.read_bytes()==other.read_bytes(),str(p)
            count+=1
    return count

def verify(out):
    out=out.resolve();assert out.is_relative_to(s.OUT) and not out.exists()
    assert not list((s.OUT/'live').rglob('*.lock')) and not (s.OUT/'task_api.lock').exists()
    out.mkdir(parents=True)
    with ExitStack() as stack:
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('011 replay forbids network')))
        auth=s.read_json(s.OUT/'authority_001.json')
        assert auth['native_stage_sha256']==s.pilot.digest_file(s.TASK/'native_stage011.py')
        assert auth['protocol_sha256']==s.pilot.digest_file(s.OUT/'execution_protocol_001.md')
        assert auth['stage_caps_cny']==s.STAGE_CAPS and sum(s.STAGE_CAPS.values())==40
        for path,digest in auth['immutable_source_sha256'].items():assert s.pilot.digest_file(s.ROOT/path)==digest
        old=s.read_json(s.OUT/'readiness_001/history_before_hashes.json')
        assert all(s.pilot.digest_file(s.ROOT/path)==digest for path,digest in old.items())
        for v in (1,2):
            for folder in (f'offline_00{v}',f'offline_review_00{v}'):
                m=s.read_json(s.OUT/folder/'manifest.json')
                for path,digest in m['files'].items():assert s.pilot.digest_file(s.OUT/folder/path)==digest
                for path,digest in m['dependencies'].items():assert s.pilot.digest_file(s.ROOT/path)==digest
                for path,digest in m['code_sha256'].items():
                    actual=s.ROOT/path
                    snapshot=s.OUT/f'development_history_00{v}'/actual.name
                    if s.pilot.digest_file(actual)!=digest:
                        assert snapshot.exists() and s.pilot.digest_file(snapshot)==digest
        for name in ('offline_003','offline_review_003','readiness_001','pilot_preparation_001','main_preparation_001','input_diagnostics_001','input_context_diagnostics_001','pilot_analysis_001'):s.check(s.OUT/name)
        records={r['proposition_id']:r for r in s.pilot.jsonl(s.OUT/'offline_003/inputs.jsonl')}
        prompts=s.read_json(s.OUT/'offline_003/judge_prompts.json')
        for phase in s.STAGE_CAPS:
            prep=s.OUT/f'{phase}_preparation_001'
            jobs={j['request_id']:j for j in s.pilot.jsonl(prep/'jobs.jsonl')}
            for a in s.pilot.read_csv(prep/'assignments.csv')[1]:
                item=records[a['proposition_id']]
                body=s.judge_body(item,item['retrieval'][a['arm']]['reference'],prompts)
                assert body==jobs[a['request_id']]['body']
                assert s.pilot.fingerprint(body)==a['body_sha256']
                assert a['request_id']==phase+':r'+a['round']+':'+a['body_sha256']
            assert list(jobs)==sorted(jobs,key=lambda rid:s.pilot.digest_text('011/schedule/v1:'+rid))
        count=0
        with redirect_stdout(io.StringIO()):
            prepare(out/'offline_replay')
            count+=equal_content(s.OUT/'offline_003',out/'offline_replay')
            diagnose(out/'input_diagnostics_replay')
            count+=equal_content(s.OUT/'input_diagnostics_001',out/'input_diagnostics_replay')
            diagnose_context(out/'context_diagnostics_replay')
            count+=equal_content(s.OUT/'input_context_diagnostics_001',out/'context_diagnostics_replay')
            score('pilot',out/'pilot_replay')
            count+=equal_content(s.OUT/'pilot_analysis_001',out/'pilot_replay')
            gate=s.read_json(s.OUT/'pilot_analysis_001/gate.json')
            if gate['proceed_main']:
                s.check(s.OUT/'main_analysis_001');score('main',out/'main_replay')
                count+=equal_content(s.OUT/'main_analysis_001',out/'main_replay')
            else:assert not (s.OUT/'live/main').exists(),'Main ran despite negative gate'
            if (s.OUT/'case_analysis_001/manifest.json').exists():
                from render_analysis011 import render
                s.check(s.OUT/'pilot_review_001');s.check(s.OUT/'case_analysis_001')
                render('pilot',s.TASK/'case_notes.json',out/'case_replay')
                count+=equal_content(s.OUT/'case_analysis_001',out/'case_replay')
        cost=sum(s.read_json(s.OUT/f'{phase}_analysis_001/summary.json')['cost_cny'] for phase in s.STAGE_CAPS if (s.OUT/f'{phase}_analysis_001').exists())
        assert cost<=40
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
        (out/'tests.log').write_text(log.getvalue(),encoding='utf-8')
        assert result.wasSuccessful()
        report=dict(tests=result.testsRun,success=True,replayed_content_files=count,history_files_unchanged=len(old),
            network_blocked=True,new_api_calls=0,total_cost_or_reserved_cny=cost,gate_proceed_main=gate['proceed_main'],
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
            tracked_changes=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines(),
            workspace_changes_informational=True,independent_audit=False)
        s.pilot.write_json(out/'verification.json',report)
        s.seal(out,[s.OUT/'authority_001.json'],[Path(__file__)])
    print(s.pilot.canonical(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    verify(p.parse_args().output)
