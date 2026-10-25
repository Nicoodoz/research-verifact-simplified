"""Offline replay and bounded negative checks, not an independent research audit."""
from contextlib import redirect_stdout, redirect_stderr
import argparse
import copy
import io
from pathlib import Path
import socket
import subprocess
import unittest
import common014 as c
from analyze014 import analyze
from replay_history import check_history

def compare_body(job,record):
    b=copy.deepcopy(record['baseline_body']);b['model']=c.MODEL
    c.require(job['body']==b,'Only model may change')
    c.require(job['proposition_id']==record['proposition_id'],'Patient/claim mapping mismatch')
    c.require(job['request_id']=='qwen:'+c.fingerprint(b),'Request ID mismatch')

def verify(out):
    c.require(not out.exists(),'Verification output exists')
    out.mkdir(parents=True)
    old_connect=socket.socket.connect
    def blocked(*args,**kwargs):raise RuntimeError('Verification network blocked')
    socket.socket.connect=blocked
    try:
        manifest=c.verify_preparation()
        baseline=c.jsonlines(c.OUT/'preparation_001/baseline_records.jsonl')
        records={r['proposition_id']:r for r in baseline}
        jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl')
        for j in jobs:compare_body(j,records[j['proposition_id']])
        negative=[]
        j=jobs[0];r=records[j['proposition_id']]
        for field in ('model','temperature','max_tokens','enable_thinking','messages','response_format'):
            bad=copy.deepcopy(j);bad['body'][field]='tampered'
            try:compare_body(bad,r)
            except ValueError:negative.append(field)
            else:raise AssertionError('Tampered body accepted')
        bad=copy.deepcopy(j);bad['proposition_id']='another_patient_claim'
        try:compare_body(bad,r)
        except ValueError:negative.append('claim_mapping')
        else:raise AssertionError('Wrong mapping accepted')
        original=c.read(c.OUT/'analysis_001/manifest.json')
        c.check_hashes(original['files']);c.check_hashes(original['code_sha256']);c.check_hashes(original['dependencies'])
        with redirect_stdout(io.StringIO()):analyze(out/'replay')
        compared=[]
        for p in (out/'replay').rglob('*'):
            if p.is_file() and p.name!='manifest.json':
                name=p.relative_to(out/'replay')
                c.require(p.read_bytes()==(c.OUT/'analysis_001'/name).read_bytes(),'Replay mismatch '+str(name))
                compared.append(str(name))
        m=c.read(c.OUT/'analysis_001/metrics.json')
        historical=c.read(c.OLD/'analysis_001/metrics.json')
        for author in ('llm','human'):
            c.require(m[author]['v4_010']==historical[author]['metrics']['c48_reference'],'V4 full metrics differ from 010')
        from render_review014 import render
        from render_report014 import run as render_report
        render(out/'review_replay')
        for p in (out/'review_replay').iterdir():
            if p.name!='manifest.json':
                c.require(p.read_bytes()==(c.OUT/'review_001'/p.name).read_bytes(),'Review replay mismatch '+p.name)
                compared.append('review/'+p.name)
        render_report(out/'report.md')
        c.require((out/'report.md').read_bytes()==(c.OUT/'report.md').read_bytes(),'Report replay mismatch')
        compared.append('report.md')
        cohort=c.csvrows(c.OUT/'preparation_001/cohort.csv')
        qpred=c.csvrows(c.OUT/'analysis_001/predictions_qwen.csv')
        for label,pp in [('missing',qpred[:-1]),('duplicate',qpred+[qpred[0]]),('illegal',[dict(qpred[0],verdict='unknown')]+qpred[1:])]:
            try:c.evaluate(cohort,pp,profile='none')
            except ValueError:negative.append(label)
            else:raise AssertionError('Invalid predictions accepted')
        history=c.read(c.OUT/'preparation_001/history_sha256.json');history_status=check_history(history)
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):
            tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(c.ROOT/'tests')))
        (out/'tests.log').write_text(log.getvalue(),encoding='utf-8',newline='\n')
        c.require(tests.wasSuccessful(),'Tests failed; inspect log')
        history_status=check_history(history)
        result=dict(created_utc=c.now(),tests=tests.testsRun,tests_passed=True,negative_checks=negative,
            exact_model_only_bodies=len(jobs),replayed_content_files=len(compared),history_files_unchanged=history_status['strict_unchanged_files'],history_validation=history_status,
            full_v4_metrics_identical_to_010=True,network_blocked=True,api_calls=0,independent_audit=False,
            head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT).decode().strip())
        c.write_json(out/'verification.json',result)
    finally:socket.socket.connect=old_connect
    print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);verify(p.parse_args().output.resolve())
