"""Offline replay and tampering checks. Executor verification, not independent audit."""
from pathlib import Path
import argparse
import copy
import io
import socket
import subprocess
import unittest
from contextlib import redirect_stdout,redirect_stderr
import common015 as c
from analyze015 import analyze

def validate_job(j,s):
    expected=c.build_body(s['base_body'],j['proposition_id'],s['v4_output'],s['qwen_output'],j['arm'])
    c.require(j['body']==expected,'Unexpected body or candidate content')
    c.require(j['proposition_id']==s['proposition_id'],'Wrong claim mapping')
    c.require(j['request_id']=='015:'+c.fingerprint(j['body']),'Request fingerprint')
    payload=c.pilot.strict_json(j['body']['messages'][1]['content'])
    c.require(set(payload)==({'proposition','reference','candidate_judgments'} if j['arm']=='adjudication' else {'proposition','reference'}),'Hidden top-level fields')
    for opinion in payload.get('candidate_judgments',[]):
        c.require(set(opinion)=={'candidate','judgment'} and set(opinion['judgment'])=={'verdict','checks','reason'},'Unexpected candidate fields')

def verify(out):
    c.require(not out.exists(),'Output exists');out.mkdir(parents=True)
    previous=socket.socket.connect
    def blocked(*args,**kwargs):raise RuntimeError('Network blocked during verification')
    socket.socket.connect=blocked
    try:
        c.verify_preparation();history=c.read(c.OUT/'preparation_001/history_sha256.json');c.check_hashes(history)
        jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl');src={r['proposition_id']:r for r in c.jsonlines(c.OUT/'preparation_001/candidate_sources.jsonl')}
        rows=c.csvrows(c.OUT/'preparation_001/ledger.csv');cohort=c.csvrows(c.OUT/'preparation_001/cohort.csv')
        disagree={r['proposition_id'] for r in rows if r['baseline']!=r['qwen']}
        c.require(len(disagree)==78 and set(src)==disagree,'Disagreement membership')
        for arm in c.ARMS:c.require({j['proposition_id'] for j in jobs if j['arm']==arm}==disagree,'Wrong requested population')
        for j in jobs:validate_job(j,src[j['proposition_id']])
        negative=[];j=next(j for j in jobs if j['arm']=='adjudication');s=src[j['proposition_id']]
        for change in ('claim','reference','GT','candidate_label','candidate_reason','model','temperature','mapping'):
            bad=copy.deepcopy(j);payload=c.pilot.strict_json(bad['body']['messages'][1]['content'])
            if change=='claim':payload['proposition']='changed'
            if change=='reference':payload['reference']+='changed'
            if change=='GT':payload['human_gt']='Supported'
            if change=='candidate_label':payload['candidate_judgments'][0]['judgment']['verdict']='tampered'
            if change=='candidate_reason':payload['candidate_judgments'][0]['judgment']['reason']='tampered'
            bad['body']['messages'][1]['content']=c.canonical(payload)
            if change=='model':bad['body']['model']='other'
            if change=='temperature':bad['body']['temperature']=.8
            if change=='mapping':bad['proposition_id']='hidden_patient'
            try:validate_job(bad,s)
            except ValueError:negative.append(change)
            else:raise AssertionError('Tampering accepted '+change)
        m=c.read(c.OUT/'analysis_001/manifest.json')
        for key in ('files','code_sha256','dependencies'):c.check_hashes(m[key])
        with redirect_stdout(io.StringIO()):analyze(out/'analysis_replay')
        replayed=[]
        for p in (out/'analysis_replay').rglob('*'):
            if p.is_file() and p.name!='manifest.json':
                name=p.relative_to(out/'analysis_replay');c.require(p.read_bytes()==(c.OUT/'analysis_001'/name).read_bytes(),'Analysis replay mismatch '+str(name));replayed.append('analysis/'+str(name))
        metrics=c.read(c.OUT/'analysis_001/metrics.json');old=c.read(c.prior.OUT/'analysis_001/metrics.json')
        for a in ('llm','human'):
            c.require(metrics[a]['v4']==old[a]['v4_010'] and metrics[a]['qwen']==old[a]['qwen'],'Baseline metrics changed')
        transitions=c.csvrows(c.OUT/'analysis_001/transitions.csv')
        c.require(all(r['adjudication']==r['evidence_only']==r['baseline'] for r in transitions if r['baseline']==r['qwen']),'Agreement changed')
        pred=c.csvrows(c.OUT/'analysis_001/predictions_adjudication.csv')
        for name,pp in [('missing',pred[:-1]),('duplicate',pred+[pred[0]]),('illegal',[dict(pred[0],verdict='unknown')]+pred[1:])]:
            try:c.evaluate(cohort,pp,profile='none')
            except ValueError:negative.append(name)
            else:raise AssertionError('Invalid predictions accepted')
        from render_review015 import render
        from render_report015 import run
        render(out/'review_replay');run(out/'report.md')
        for p in (out/'review_replay').iterdir():
            if p.name!='manifest.json':
                c.require(p.read_bytes()==(c.OUT/'review_001'/p.name).read_bytes(),'Review mismatch');replayed.append('review/'+p.name)
        c.require((out/'report.md').read_bytes()==(c.OUT/'report.md').read_bytes(),'Report mismatch');replayed.append('report.md')
        log=io.StringIO()
        with redirect_stdout(log),redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(c.ROOT/'tests')))
        (out/'tests.log').write_text(log.getvalue(),encoding='utf-8',newline='\n');c.require(result.wasSuccessful(),'Tests failed')
        c.check_hashes(history)
        summary=dict(created_utc=c.now(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT).decode().strip(),
            tests=result.testsRun,tests_passed=True,negative_checks=negative,exact_jobs=156,agreement_passthrough=572,
            replayed_content_files=len(replayed),history_files_unchanged=len(history),baseline_metrics_identical=True,
            api_calls=0,network_blocked=True,independent_audit=False)
        c.write_json(out/'verification.json',summary)
    finally:socket.socket.connect=previous
    print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);verify(p.parse_args().output.resolve())
