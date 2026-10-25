"""Offline invariants/tests plus standing task-budget authorization registration."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
import io
import unittest
import study011 as s

if __name__=='__main__':
    assert not (s.OUT/'authority_001.json').exists()
    for name in ('offline_003','offline_review_003','pilot_preparation_001','main_preparation_001'):s.check(s.OUT/name)
    assert s.read_json(s.OUT/'offline_review_003/reading_conclusion.json')['allow_pilot']
    expected=sum(s.read_json(s.OUT/f'{phase}_preparation_001/summary.json')['expected_peak_cny'] for phase in s.STAGE_CAPS)
    assert expected<=40
    inputs={r['proposition_id']:r for r in s.pilot.jsonl(s.OUT/'offline_003/inputs.jsonl')}
    prompts=s.read_json(s.OUT/'offline_003/judge_prompts.json')
    bound=0
    for phase in s.STAGE_CAPS:
        jobs={j['request_id']:j for j in s.pilot.jsonl(s.OUT/f'{phase}_preparation_001/jobs.jsonl')}
        for a in s.pilot.read_csv(s.OUT/f'{phase}_preparation_001/assignments.csv')[1]:
            item=inputs[a['proposition_id']];body=s.judge_body(item,item['retrieval'][a['arm']]['reference'],prompts)
            assert jobs[a['request_id']]['body']==body and s.pilot.fingerprint(body)==a['body_sha256']
            assert set(s.pilot.strict_json(body['messages'][1]['content']))=={'proposition','reference'}
            bound+=1
    out=s.OUT/'readiness_001';out.mkdir()
    log=io.StringIO()
    with ExitStack() as stack,redirect_stdout(log),redirect_stderr(log):
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            stack.enter_context(patch(target,side_effect=AssertionError('Network prohibited')))
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(s.ROOT/'tests')))
    (out/'tests.log').write_text(log.getvalue(),encoding='utf-8')
    assert result.wasSuccessful()
    protected={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for task in ('009_retrieval_baselines','010_verifact_baseline_alignment') for category in ('tasks','outputs') for p in (s.ROOT/category/task).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    s.pilot.write_json(out/'history_before_hashes.json',protected)
    s.pilot.write_json(out/'checks.json',dict(tests=result.testsRun,success=True,network_disabled=True,logical_bodies_checked=bound,api_calls=0))
    code=[s.TASK/n for n in ('study011.py','packaging011.py','io011.py','score011.py','build_jobs011.py','prepare011.py')]
    code += [s.ROOT/n for n in ('tasks/008_retrieval_planning/build_stages.py','tasks/008_retrieval_planning/services.py','tasks/008_retrieval_planning/planning_core.py','tasks/004_event_alignment_pilot/siliconflow.py','src/verifact_research/evaluation/core.py','src/verifact_research/evaluation/metrics.py')]
    code += [s.OUT/'offline_review_003/reading_conclusion.json']
    s.seal(out,[s.OUT/'offline_003/manifest.json'],[Path(__file__),s.TASK/'native_stage011.py'])
    s.pilot.write_json(s.OUT/'authority_001.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        authority='User task011 plus AGENTS <=40 CNY standing task-total rule; main additionally requires predefined pilot gate',
        expected_total_cny=expected,task_cap_cny=40,stage_caps_cny=s.STAGE_CAPS,
        native_stage_sha256=s.pilot.digest_file(s.TASK/'native_stage011.py'),protocol_sha256=s.pilot.digest_file(s.OUT/'execution_protocol_001.md'),
        immutable_source_sha256={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in code},tests=result.testsRun,head=s.BASE_HEAD))
    print('Registered; tests',result.testsRun,'expected total',expected,'history',len(protected))
