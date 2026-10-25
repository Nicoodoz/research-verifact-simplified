"""Offline integration, replay, and historical-integrity verification for019."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
import argparse, copy, io, json, shutil, socket, tempfile, unittest
import common019 as c
import analysis019 as a

def no_network(*args,**kwargs): raise RuntimeError('Network disabled for offline verification')

def integration():
    original_out=c.OUT
    with tempfile.TemporaryDirectory(prefix='019-synthetic-analysis-') as d:
        root=Path(d);out=root/'out';prep=out/'selection/preparation';prep.mkdir(parents=True)
        jobs=[];rows=[];assign=[];progress={}
        for i in range(12):
            gt=c.LABELS[i%3];pid=f'synthetic_{i}';sid=f'patient_{i//2}'
            row=dict(proposition_id=pid,subject_id=sid,author_type='llm' if i%2==0 else 'human',human_gt=gt,C='Not Supported',O=gt,case_id=pid);rows.append(row)
            for arm in ('B','S'):
                rid=pid+'/'+arm;body=c.body('Synthetic statement '+str(i),'[1] Synthetic record.',arm=='S')
                job=dict(request_id=rid,stage='selection',arm=arm,repeat=0,proposition_id=pid,body=body);jobs.append(job)
                obj=dict(verdict='Not Supported',reason='Synthetic fixture.',checks=[])
                if arm=='S':obj['label_scores']=dict(zip(c.LABELS,[45,50,5] if i%3==0 else [5,80,15]))
                native=dict(model=c.MODEL,choices=[dict(finish_reason='stop',message=dict(content=json.dumps(obj)))],usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2))
                rec=dict(request_id=rid,job_sha256=c.fingerprint(job),actual_body=body,actual_body_sha256=c.fingerprint(body),attempt=1,provider='fake_offline',account='fake',transport=dict(http_status=200,body_text=json.dumps(native)))
                f=out/f'fixture_{i}_{arm}.json';c.write_json(f,rec)
                progress[rid]=dict(status='received',attempts=1,receipts=[dict(file=f.name,sha256=c.file_hash(f))])
                assign.append(dict(proposition_id=pid,arm=arm,repeat=0,request_id=rid))
        c.write_lines(prep/'jobs.jsonl',jobs);c.write_csv(prep/'assignments.csv',assign);c.write_csv(out/'selection/cohort.csv',rows)
        c.write_json(out/'live_ledger.json',dict(phases={'selection':{'jobs':progress}}))
        captured=io.StringIO()
        with patch.object(c,'OUT',out),patch.object(c,'ROOT',root),patch.object(c,'check_manifest',return_value={}),patch.object(socket,'create_connection',no_network),redirect_stdout(captured):
            a.analyze('selection')
        decision=c.read(out/'selection_freeze.json');metrics=c.read(out/'selection/analysis_001/metrics.json')
        c.require(len(metrics)==36,'Expected all methods and strata')
        c.require(metrics['r0/all/B']['counts']['correct']==4,'Synthetic baseline count mismatch')
        c.write_json(original_out/'analysis_integration_test.json',dict(passed=True,synthetic_only=True,network_blocked=True,API_calls=0,metric_sets=len(metrics),selected=decision['selected_lambda'],decision_passed=decision['passed']))
        print('SYNTHETIC_INTEGRATION_PASS',len(metrics),'metric sets; no APIs')

def replay():
    original=c.OUT;v=original/'verification_001';v.mkdir(exist_ok=False)
    c.check_manifest(original/'authority.json')
    frozen=c.read(original/'history_before.json')['files'];changed=[n for n,h in frozen.items() if not (c.ROOT/n).is_file() or c.file_hash(c.ROOT/n)!=h]
    allowed={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md'}
    c.require(not(set(changed)-allowed),'Historical non-navigation files changed')
    target=v/'replay';target.mkdir()
    def cp(source,dest):
        if source.is_dir():
            shutil.copytree(source,dest)
            for p in source.rglob('*'):
                if p.is_file():c.require(c.file_hash(p)==c.file_hash(dest/p.relative_to(source)),'Replay copy mismatch')
        else:shutil.copy2(source,dest);c.require(c.file_hash(source)==c.file_hash(dest),'Replay copy mismatch')
    cp(original/'live_ledger.json',target/'live_ledger.json')
    stages=[s for s in ('selection','validation') if (original/s/'analysis_001/metrics.json').exists()]
    for stage in stages:
        (target/stage).mkdir()
        for name in ('preparation','live','cohort.csv','cohort_manifest.json'):cp(original/stage/name,target/stage/name)
    compared=[]
    with (v/'replay_log.txt').open('w',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log),patch.object(c,'OUT',target),patch.object(socket,'create_connection',no_network):
        for stage in stages:
            a.analyze(stage)
            for p in (original/stage/'analysis_001').iterdir():
                if p.name in ('decision.json','manifest.json'):continue
                q=target/stage/'analysis_001'/p.name
                c.require(c.file_hash(p)==c.file_hash(q),'Replay differs: '+stage+'/'+p.name)
                compared.append(stage+'/'+p.name)
    for f in ('selection_freeze.json','validation_decision.json'):
        if (original/f).exists():
            b=c.read(original/f);z=c.read(target/f);b.pop('created_utc',None);z.pop('created_utc',None)
            c.require(b==z,'Decision replay differs')
    result=dict(status='executor_offline_verification_not_independent_audit',network_blocked=True,new_API_calls=0,
        historical_files_checked=len(frozen),navigation_changes=changed,replayed_content_files=compared,decisions_equal_excluding_timestamp=True)
    c.write_json(v/'summary.json',result);print('REPLAY_PASS',len(compared),'content files; historical checks',len(frozen))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['integration','replay']);args=p.parse_args()
    integration() if args.action=='integration' else replay()
