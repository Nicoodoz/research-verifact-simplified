import sys,json,csv,hashlib,io,unittest
from pathlib import Path
from collections import Counter,defaultdict
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
from datetime import datetime,timezone
R=Path('D:/Research-VeriFact'); T=Path('C:/Users/13359/AppData/Local/Temp/verifact_007_audit_86kvk0gh')
O=R/'outputs/007_context_retrieval'; P=O/'preparation_003'; U=O/'run_001'; S=O/'zero_budget_sensitivity_001'
j=lambda p:json.loads(p.read_text(encoding='utf-8'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
H=j(T/'handoff.json'); assert all(h(R/n)==d for n,d in H['file_sha256'].items())
result={'head':H['head'],'handoff_sha256':h(T/'handoff.json'),'version_files':len(H['file_sha256']),'started_utc':datetime.now(timezone.utc).isoformat()}
sys.path.insert(0,str(R/'tasks/007_context_retrieval'))
with ExitStack() as g:
    for n in ('socket.socket.connect','socket.socket.connect_ex','socket.create_connection'):
        g.enter_context(patch(n,side_effect=AssertionError('No audit network')))
    suite=unittest.defaultTestLoader.discover(str(R/'tests'),pattern='test_context_retrieval.py')
    with (T/'tests.log').open('w',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log):
        test=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert test.wasSuccessful(); result['targeted_tests']=test.testsRun
    import prepare as p
    import retrieval as rt
    import score_results as scoring
    from run_judge import charge_for
    from zero_budget_sensitivity import pack_saved
    inputs={x['proposition_id']:x for x in p.pilot.jsonl(P/'inputs.jsonl')}
    additional={x['proposition_id']:x for x in p.pilot.jsonl(S/'inputs.jsonl')}
    cohort=rows(P/'cohort.csv'); pool=rows(P/'candidate_universe.csv'); split=j(R/'outputs/003_error_analysis/patient_groups.json')
    patients=sorted(split['groups']['development'],key=lambda x:hashlib.sha256((split['seed']+x).encode()).hexdigest())[8:12]
    assert patients==['21706','55204','65399','47874'] and len(cohort)==96 and len(pool)==406
    assert set(x['subject_id'] for x in cohort)==set(patients) and not set(patients)&set(split['groups']['reserved_test'])
    master=rows(R/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv')
    assert pool==[x for x in master if x['subject_id'] in patients and x['proposition_type']=='claim' and x['invalid']=='False']
    chosen=[]
    for sid in patients:
        for author in ('llm','human'):
            group=sorted([x for x in pool if x['subject_id']==sid and x['author_type']==author],key=lambda x:hashlib.sha256(('007_context_retrieval/selection/v1:'+x['proposition_id']).encode()).hexdigest())
            part=sum(([x for x in group if x['human_gt']==label][:3] for label in ('Not Supported','Not Addressed')),[])
            part += [x for x in group if x['human_gt']=='Supported'][:12-len(part)]
            part += [x for x in group if x not in part][:12-len(part)]; chosen+=part
    assert sorted(chosen,key=lambda x:int(x['human_csv_order']))==cohort
    corpora=j(P/'corpora.json')
    notes=p.pilot.subset_csv(p.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',set(corpora))
    note_by={x['ROW_ID']:x for x in notes}
    admissions={p.pilot.integer_id(x['SUBJECT_ID']):x for x in p.pilot.subset_csv(p.RAW/'reference_ehr/admissions.csv.gz','SUBJECT_ID',set(corpora))}
    spans=defaultdict(list)
    for sid,corpus in corpora.items():
        admission=admissions[sid]
        for x in corpus:
            raw=note_by[x['note_id']]
            assert p.pilot.integer_id(raw['SUBJECT_ID'])==sid and admission['ADMITTIME'][:10]<=raw['CHARTDATE'][:10]<=admission['DISCHTIME'][:10]
            assert raw['CATEGORY'].strip().lower()!='discharge summary'
            assert x['text']==raw['TEXT'][x['start']:x['end_exclusive']] and p.pilot.digest_text(raw['TEXT'])==x['note_sha256']
            spans[x['note_id']].append((x['start'],x['end_exclusive']))
    for nid,intervals in spans.items():
        text=note_by[nid]['TEXT']; end=0
        for lo,hi in sorted(intervals):assert lo>=end and not text[end:lo].strip();end=hi
        assert not text[end:].strip()
    indexes={sid:rt.BM25(corpora[sid]) for sid in patients}
    props=p.pilot.subset_csv(p.RAW/'propositions/propositions.csv.gz','subject_id',set(patients))
    prop_by={x['proposition_id']:x for x in props}
    for pid,x in inputs.items():
        source=prop_by[pid]; assert x['text']==source['text'] and x['queries']['claim']==source['text']
        parent=source['parent_text_chunk']; bhc=source['brief_hospital_course']; assert bhc.count(parent)==1
        pos=bhc.index(parent); assert x['queries']['local']==bhc[max(0,pos-240):pos+len(parent)]
        sentences=[v for v in props if v['subject_id'].removesuffix('.0')==x['subject_id'] and v['author_type']==x['author_type'] and v['proposition_type']=='sentence']
        assert rt.sentence_query(x['text'],parent,sentences)[0]==x['queries']['sentence']
        rebuilt=rt.retrieve(indexes[x['subject_id']],x['queries'])
        for arm in rt.ARMS:
            assert rt.reference(rebuilt[arm],x['admission'])==x['retrieval'][arm]['reference']
            assert [r['passage_id'] for r in rebuilt[arm]['top100']]==[r['passage_id'] for r in x['retrieval'][arm]['top100']]
    zero={pid for pid,x in inputs.items() if x['retrieval']['claim']['matched_character_budget']==0}
    assert zero==set(additional) and {inputs[pid]['case_id'] for pid in zero}=={'R031','R078','R083'}
    for pid,x in additional.items():
        for arm,res in x['retrieval'].items():
            packed=pack_saved(corpora[x['subject_id']],inputs[pid]['retrieval'][arm]['top100'])
            assert rt.reference(packed,x['admission'])==res['reference']
    bodies=defaultdict(list); answers={}; total=0; costs={}; account_set=set(); settings=set(); systems=set()
    auth=j(O/'authorization_001.json'); plan=j(S/'protocol_and_authority.json')
    assert plan['primary_used_cny']+1==plan['cumulative_task_upper_guard_cny']<=16
    for stage,prep,run,registered,items in [('primary',P,U,auth['registered_utc'],inputs),('supplementary',S,S/'receipts',plan['registered_utc'],additional)]:
        jobs=p.pilot.jsonl(prep/'requests.jsonl'); state=j(run/'state.json'); manifest=j(run/'manifest.json')
        assert manifest['jobs']==jobs and state['run_id']==p.pilot.fingerprint(manifest)
        amount=0
        for i,job in enumerate(jobs,1):
            rid=job['request_id']; arm,pid=rid.split(':',1); x=items[pid]; body=job['body']; user=json.loads(body['messages'][1]['content'])
            assert set(user)=={'proposition','reference'} and user['proposition']==inputs[pid]['text']
            assert user['reference']==x['retrieval']['claim' if arm=='claim_repeat' else arm]['reference']
            systems.add(body['messages'][0]['content']); settings.add(json.dumps({k:v for k,v in body.items() if k!='messages'},sort_keys=True))
            progress=state['jobs'][rid]; assert progress['attempts']==len(progress['receipts'])==1 and progress['status']=='response_received'
            pointer=progress['receipts'][0]; assert pointer['file']==f'receipt_{i:06d}_001.json' and h(run/pointer['file'])==pointer['sha256']
            rec=j(run/pointer['file']); assert rec['request_id']==rid and rec['request_sha256']==p.pilot.fingerprint(body) and rec['run_id']==state['run_id']
            tr=rec['transport']; assert tr['http_status']==200 and tr['started_utc']>=registered
            response=json.loads(tr['body_text']); choice=response['choices'][0]
            assert choice['finish_reason']=='stop' and response['model']=='deepseek-ai/DeepSeek-V4-Flash'
            verdict=json.loads(choice['message']['content'])['verdict']; assert verdict in p.pilot.LABELS
            amount+=charge_for(tr,job['max_cost_cny'])[0]; account_set.add(rec['account'])
            if stage=='primary':answers[rid]=verdict;bodies[p.pilot.fingerprint(body)].append(rid)
            else:
                norm=scoring.normalize(job,x,tr); assert norm['status']=='success'
                assert norm==next(v for v in p.pilot.jsonl(S/'normalized_responses.jsonl') if v['request_id']==rid)
        assert len(list(run.glob('receipt_*.json')))==len(jobs) and abs(amount-state['reserved_budget_cny'])<1e-10
        costs[stage]=amount;total+=amount
    assert len(settings)==len(systems)==1 and total<16 and len(answers)==392
    duplicate=[v for v in bodies.values() if len(v)>1]; disagreements=sum(len({answers[r] for r in ids})>1 for ids in duplicate)
    repeats=[r for r in answers if r.startswith('claim_repeat:')];repeat_changes=sum(answers[r]!=answers[r.replace('claim_repeat:','claim:',1)] for r in repeats)
    assert (len(duplicate),disagreements,len(repeats),repeat_changes)==(30,8,8,2)
    with redirect_stdout(io.StringIO()):scoring.score(P,U,T/'replay')
    expected=j(U/'analysis/manifest.json')['output_sha256'];same={n:h(U/'analysis'/n)==h(T/'replay'/n) for n in expected};assert all(same.values())
    metrics=j(T/'replay/metrics.json'); anchors=j(U/'review_001/semantic_001/evidence_anchors.json')
    supp_norm={x['request_id']:x for x in p.pilot.jsonl(S/'normalized_responses.jsonl')}
    for a in anchors:
        packet=j(U/'review_001/packets'/(a['case_id']+'.json'));pid=packet['case']['proposition_id']
        if a['source']=='released_reference':text=packet['released_reference']['reference']
        elif a['source']=='ehr_reference':
            item=inputs[pid] if a['stage']=='main' else additional[pid];text=item['retrieval'][a['arm']]['reference']
            raw=note_by[a['note_id']]; assert p.pilot.digest_text(raw['TEXT'])==a['note_sha256']
        else:text=(packet['responses'][a['arm']] if a['stage']=='main' else supp_norm[a['arm']+':'+pid])['output_text']
        assert p.pilot.digest_text(text)==a['source_sha256'] and text[a['start']:a['end_exclusive']]==a['quote']
    assert all(h(R/n)==d for n,d in H['file_sha256'].items())
    result.update(status='limited_mechanical_audit_pass',patients=patients,claims=96,indexed_spans=sum(map(len,corpora.values())),raw_note_coverage_checked=len(spans),rankings_and_references_rebuilt=96*4,attempts=404,valid=404,account_aliases=sorted(account_set),costs=costs,total_estimated_cny=total,same_body_groups=len(duplicate),same_body_disagree=disagreements,repeat_changes=repeat_changes,primary_delta={a:metrics[a]['contrasts']['mixed_minus_claim']['metrics']['mcc'] for a in ('llm','human')},zero_budget_cases=sorted(inputs[pid]['case_id'] for pid in zero),score_files_identical=same,anchors_verified=len(anchors),submitted_files_unchanged=True,new_api_calls=0,finished_utc=datetime.now(timezone.utc).isoformat())
(T/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='score_files_identical'},ensure_ascii=False))
