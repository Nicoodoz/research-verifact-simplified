"""Offline readiness then receipt-bound task authority from the existing 40-CNY rule."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
import io
import unittest
import subprocess
import alignment_common as s

if __name__=='__main__':
    assert not (s.OUT/'authority_001.json').exists()
    s.check(s.OUT/'preparation_001')
    summary=s.read_json(s.OUT/'preparation_001/summary.json')
    assert summary['estimated_peak_cny']<=40
    jobs=s.pilot.jsonl(s.OUT/'preparation_001/jobs.jsonl')
    assignments=s.pilot.read_csv(s.OUT/'preparation_001/assignments.csv')[1]
    inputs={x['proposition_id']:x for x in s.pilot.jsonl(s.OUT/'preparation_001/inputs.jsonl')}
    byid={j['request_id']:j for j in jobs}
    prompts=s.read_json(s.OUT/'preparation_001/judge_prompts.json')
    for a in assignments:
        item=inputs[a['proposition_id']]
        expected=s.judge_body(item,item['references'][a['arm']],prompts)
        assert byid[a['request_id']]['body']==expected and s.pilot.fingerprint(expected)==a['body_sha256']
        assert set(s.pilot.strict_json(expected['messages'][1]['content']))=={'proposition','reference'}
    for r in s.read_json(s.OUT/'preparation_001/repeats.json'):
        assert byid[r['request_id']]['body']==byid[r['canonical_request_id']]['body']
    out=s.OUT/'readiness_001'
    out.mkdir(exist_ok=False)
    log=io.StringIO()
    with ExitStack() as stack,redirect_stdout(log),redirect_stderr(log):
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('Network prohibited')))
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
    (out/'tests.log').write_text(log.getvalue(),encoding='utf-8')
    assert result.wasSuccessful()
    s.pilot.write_json(out/'checks.json',dict(tests=result.testsRun,success=True,network_disabled=True,complete_bodies_checked=len(jobs),assignments_checked=len(assignments),api_calls=0))
    protected={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in (s.ROOT/'outputs/009_retrieval_baselines').rglob('*') if p.is_file()}
    s.pilot.write_json(out/'009_before_hashes.json',protected)
    s.seal(out,[s.OUT/'preparation_001/manifest.json'],[Path(__file__),s.TASK/'native_stage010.py',s.TASK/'alignment_common.py'])
    code=[s.TASK/'alignment_common.py',s.TASK/'io010.py',s.TASK/'prepare_alignment.py',
        s.ROOT/'tasks/008_retrieval_planning/build_stages.py',s.ROOT/'tasks/008_retrieval_planning/services.py',
        s.ROOT/'tasks/004_event_alignment_pilot/siliconflow.py',s.ROOT/'src/verifact_research/evaluation/core.py',s.ROOT/'src/verifact_research/evaluation/metrics.py']
    s.pilot.write_json(s.OUT/'authority_001.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),authority='User task010 plus AGENTS task total <=40 CNY standing authorization; no extra paid preflight',
        expected_total_cny=summary['estimated_peak_cny'],task_cap_cny=40,stage_caps_cny=s.STAGE_CAPS,
        native_stage_sha256=s.pilot.digest_file(s.TASK/'native_stage010.py'),protocol_sha256=s.pilot.digest_file(s.OUT/'execution_protocol_001.md'),
        immutable_source_sha256={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in code},
        preparation_manifest_sha256=s.pilot.digest_file(s.OUT/'preparation_001/manifest.json'),tests=result.testsRun,head=s.BASE_HEAD))
    print('Readiness and 40-CNY task authority recorded; tests',result.testsRun,'requests',len(jobs),'expected',summary['estimated_peak_cny'])
