import sys,json,hashlib,csv,gzip,re,io,unittest
from pathlib import Path
from collections import Counter
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
from datetime import datetime,timezone
R=Path('D:/Research-VeriFact'); T=Path('C:/Users/13359/AppData/Local/Temp/verifact_006_audit_0r7nete5')
O=R/'outputs/006_source_context_feasibility'; P=O/'preparation_001'; U=O/'run_001'
j=lambda p:json.loads(p.read_text(encoding='utf-8'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
H=j(T/'handoff_snapshot.json'); assert all(h(R/n)==d for n,d in H['file_sha256'].items())
result={'head':H['head'],'handoff_sha256':h(T/'handoff_snapshot.json'),'version_files':len(H['file_sha256']), 'started_utc':datetime.now(timezone.utc).isoformat()}
sys.path.insert(0,str(R/'tasks/006_source_context_feasibility'))
with ExitStack() as g:
    for n in ('socket.socket.connect','socket.socket.connect_ex','socket.create_connection'):
        g.enter_context(patch(n,side_effect=AssertionError('Audit network disabled')))
    suite=unittest.defaultTestLoader.discover(str(R/'tests'),pattern='test_source_context*.py')
    with (T/'tests.log').open('w',encoding='utf-8') as f,redirect_stdout(f),redirect_stderr(f):
        test=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    assert test.wasSuccessful(); result['targeted_tests']=test.testsRun
    import context_feasibility as cf
    import score_context_pilot as scoring
    jobs=cf.pilot.jsonl(P/'requests.jsonl'); inputs={x['proposition_id']:x for x in cf.pilot.jsonl(P/'inputs.jsonl')}
    cohort=rows(P/'cohort.csv'); universe=rows(P/'candidate_universe.csv')
    split=j(R/'outputs/003_error_analysis/patient_groups.json')
    order=sorted(split['groups']['development'],key=lambda x:hashlib.sha256((split['seed']+x).encode()).hexdigest())
    assert order[6:8]==['45115','89909']; assert {x['subject_id'] for x in cohort}==set(order[6:8])
    assert len(cohort)==64 and len(universe)==224 and not set(order[6:8])&set(split['groups']['reserved_test'])
    master=rows(R/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv')
    actual_universe=[x for x in master if x['subject_id'] in order[6:8] and x['proposition_type']=='claim' and x['invalid']=='False']
    assert universe==actual_universe
    chosen=[]
    for sid in order[6:8]:
        for a in ('llm','human'):
            group=sorted([x for x in universe if x['subject_id']==sid and x['author_type']==a],key=lambda x:hashlib.sha256(('006_source_context_feasibility/selection/v1:'+x['proposition_id']).encode()).hexdigest())
            take=[x for label in ('Not Supported','Not Addressed') for x in group if x['human_gt']==label][:0]
            take=sum(([x for x in group if x['human_gt']==label][:5] for label in ('Not Supported','Not Addressed')),[])
            take += [x for x in group if x['human_gt']=='Supported'][:16-len(take)]
            take += [x for x in group if x not in take][:16-len(take)]
            chosen+=take
    assert sorted(chosen,key=lambda x:int(x['human_csv_order']))==cohort
    with gzip.open(R/'data/00_raw/verifact-bhc/1.1.0/propositions/propositions.csv.gz','rt',encoding='utf-8',newline='') as f:
        for p in csv.DictReader(f):
            if p['proposition_id'] not in inputs:continue
            x=inputs[p['proposition_id']]; s=x['source_context']; b=p['brief_hospital_course']; parent=p['parent_text_chunk']
            assert b.count(parent)==1 and x['text']==p['text']
            start=b.index(parent); assert s['start']==max(0,start-240) and s['end_exclusive']==start+len(parent)
            assert s['text']==b[s['start']:s['end_exclusive']] and len(s['text'])<=1200
    assert len(jobs)==192 and len({x['request_id'] for x in jobs})==192
    settings=set(); systems=set(); arms=Counter()
    for job in jobs:
        arm,pid=job['request_id'].split(':',1); x=inputs[pid]; b=job['body']; user=jtext=json.loads(b['messages'][1]['content'])
        assert set(user)=={'proposition','reference','unverified_source_text'} and user['proposition']==x['text'] and user['reference']==x['reference']
        assert hashlib.sha256(x['reference'].encode()).hexdigest()==x['reference_id']
        extra=user['unverified_source_text']
        if arm=='structured':assert extra==''
        elif arm=='source_context':assert extra==x['source_context']['text']
        else:assert all(z==x['text'] for z in extra.split('\n'))
        settings.add(json.dumps({k:v for k,v in b.items() if k!='messages'},sort_keys=True));systems.add(b['messages'][0]['content']);arms[arm]+=1
    assert len(settings)==len(systems)==1 and set(arms.values())=={64}
    state=j(U/'state.json'); amendment=j(O/'execution_amendment_001.json'); approval=j(O/'authorization_001.json')
    assert approval['approved'] and approval['budget_cny']==8 and approval['preparation_manifest_sha256']==h(P/'manifest.json')
    pending={k for k,v in amendment['original_state']['jobs'].items() if v['attempts']==0}; assert len(pending)==77
    assert j(U/'manifest.json')['jobs']==jobs
    total=0; unknown=0; accounts=set(); raw_labels={}; times=[]
    for i,job in enumerate(jobs,1):
        progress=state['jobs'][job['request_id']]; assert progress['attempts']==len(progress['receipts'])==1
        pointer=progress['receipts'][0]; assert pointer['file']==f'receipt_{i:06d}_001.json'
        receipt=j(U/pointer['file']); assert h(U/pointer['file'])==pointer['sha256']
        assert receipt['request_id']==job['request_id'] and receipt['request_sha256']==cf.pilot.fingerprint(job['body']) and receipt['attempt']==1
        tr=receipt['transport']; times.append(tr['started_utc']); assert tr['started_utc']>=approval['approved_utc']
        if job['request_id'] in pending:assert tr['started_utc']>=amendment['created_utc']
        else:assert progress==amendment['original_state']['jobs'][job['request_id']]
        accounts.add(receipt['account']); total+=pointer['estimated_charge_cny']
        if progress['status']=='unknown':
            assert progress==amendment['terminal_unknown'][job['request_id']]; unknown+=pointer['estimated_charge_cny'];continue
        native=json.loads(tr['body_text']); choice=native['choices'][0]
        assert native['model']=='deepseek-ai/DeepSeek-V4-Flash'
        if choice['finish_reason']=='stop':raw_labels[job['request_id']]=json.loads(choice['message']['content'])['verdict']
        else:assert choice['finish_reason']=='length'
    assert len(list(U.glob('receipt_*.json')))==192 and len(raw_labels)==189 and accounts=={'account_1'}
    assert abs(total-state['reserved_budget_cny'])<1e-10 and total<8
    with redirect_stdout(io.StringIO()):scoring.score(P,U,T/'replay')
    original=j(U/'analysis/manifest.json'); same={n:h(U/'analysis'/n)==h(T/'replay'/n) for n in original['output_sha256']};assert all(same.values())
    for arm in cf.ARMS:
        assert {arm+':'+x['proposition_id']:x['verdict'] for x in rows(T/'replay'/('predictions_'+arm+'.csv'))}=={k:v for k,v in raw_labels.items() if k.startswith(arm+':')}
    metrics=j(T/'replay/metrics.json')
    for a in ('llm','human'):assert metrics[a]['contrasts']['source_context_minus_structured']['status']=='blocked_incomplete_pair'
    anchors=j(U/'review_001/semantic_001/evidence_anchors.json')
    for a in anchors:
        p=j(U/'review_001/packets'/(a['case_id']+'.json'))
        s=p['input']['reference'] if a['source']=='reference' else p['input']['source_context']['text'] if a['source']=='unverified_source_window' else p['responses'][a['arm']]['output_text']
        assert hashlib.sha256(s.encode()).hexdigest()==a['source_sha256'] and s[a['start']:a['end_exclusive']]==a['quote']
    assert all(h(R/n)==d for n,d in H['file_sha256'].items())
    result.update(status='PASS_limited_mechanical_review',patients=order[6:8],claims=64,attempts=192,received=190,valid=189,unknown=2,truncated=1,continued_unsent=77,accounts=sorted(accounts),estimated_received_cny=total-unknown,unknown_reserved_cny=unknown,total_budget_cny=total,primary_comparisons_blocked=True,human_source_minus_repeat=metrics['human']['contrasts']['source_context_minus_repeat_claim'],score_files_identical=same,anchors_verified=len(anchors),version_unchanged=True,no_inference_calls=True,finished_utc=datetime.now(timezone.utc).isoformat())
(T/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('human_source_minus_repeat','score_files_identical')},ensure_ascii=False))
