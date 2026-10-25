import sys,json,hashlib,io,unittest,copy
from pathlib import Path
from collections import Counter
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from unittest.mock import patch
from datetime import datetime,timezone
R=Path('D:/Research-VeriFact'); T=Path('C:/Users/13359/AppData/Local/Temp/verifact_008_audit_zejiki1i')
O=R/'outputs/008_retrieval_planning'; P=O/'preparation_001'; U=O/'run_001'
j=lambda p:json.loads(p.read_text(encoding='utf-8'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
H=j(T/'handoff.json');assert all(h(R/n)==d for n,d in H['files_sha256'].items())
result={'head':H['base_head'],'handoff_sha256':h(T/'handoff.json'),'version_files':len(H['files_sha256']),'started_utc':datetime.now(timezone.utc).isoformat()}
sys.path.insert(0,str(R/'tasks/008_retrieval_planning'))
with ExitStack() as g:
    for n in ('socket.socket.connect','socket.socket.connect_ex','socket.create_connection'):
        g.enter_context(patch(n,side_effect=AssertionError('No audit network')))
    suite=unittest.defaultTestLoader.discover(str(R/'tests'),pattern='test_retrieval_planning.py')
    with (T/'tests.log').open('w',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log):
        test=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert test.wasSuccessful(); result['targeted_tests']=test.testsRun
    import common as c
    import planning_core as pc
    import build_stages as bs
    import check_preparation,check_judge_inputs,score_results
    import execute_phase
    from services import cost
    prep_check=check_preparation.check(); judge_check=check_judge_inputs.check()
    split=j(R/'outputs/003_error_analysis/patient_groups.json')
    order=sorted(split['groups']['development'],key=lambda x:hashlib.sha256((split['seed']+x).encode()).hexdigest())
    assert order[12:18]==c.PATIENTS and not set(c.PATIENTS)&set(split['groups']['reserved_test'])
    inputs={x['proposition_id']:x for x in c.pilot.jsonl(P/'inputs.jsonl')}
    cohort=c.pilot.read_csv(P/'cohort.csv')[1];universe=c.pilot.read_csv(P/'candidate_universe.csv')[1]
    assert len(cohort)==144 and len(universe)==494
    chosen=[]
    for sid in c.PATIENTS:
        for author in ('llm','human'):
            group=sorted([x for x in universe if x['subject_id']==sid and x['author_type']==author],key=lambda x:hashlib.sha256(('008/selection/v1:'+x['proposition_id']).encode()).hexdigest())
            part=sum(([x for x in group if x['human_gt']==label][:3] for label in ('Not Supported','Not Addressed')),[])
            part += [x for x in group if x['human_gt']=='Supported'][:12-len(part)]
            part += [x for x in group if x not in part][:12-len(part)];chosen+=part
    assert sorted(chosen,key=lambda x:int(x['human_csv_order']))==cohort
    authority=j(O/'authority_001.json'); assert authority['preparation_manifest_sha256']==h(P/'manifest.json') and sum(c.PHASE_CAPS.values())==authority['task_cap_cny']==40
    phases={}; all_values={};accounts=set()
    for phase,cap in c.PHASE_CAPS.items():
        live=O/'live'/phase; manifest=j(live/'manifest.json');state=j(live/'state.json');jobs=manifest['jobs']
        assert jobs==c.pilot.jsonl(O/execute_phase.JOB_FILES[phase]) and manifest['cap_cny']==cap
        assert c.pilot.fingerprint(manifest)==state['run_id']
        assert len(list(live.glob('receipt_*.json')))==len(jobs)
        amount=0
        for i,job in enumerate(jobs,1):
            progress=state['jobs'][job['request_id']];assert progress['status']=='received' and progress['attempts']==len(progress['receipts'])==1
            ptr=progress['receipts'][0];assert ptr['file']==f'receipt_{i:06d}_01.json' and h(live/ptr['file'])==ptr['sha256']
            rec=j(live/ptr['file']);assert rec['request_id']==job['request_id'] and rec['job_sha256']==c.pilot.fingerprint(job) and rec['attempt']==1
            assert rec['transport']['http_status']==200 and rec['transport']['started_utc']>=authority['created_utc']
            charge,basis=cost(job,rec['transport']);assert abs(charge-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'];amount+=charge
            accounts.add(rec['account'])
        assert abs(amount-state['used_or_reserved_cny'])<1e-8 and amount<=cap
        values,_=bs.phase_data(phase);all_values[phase]=values
        phases[phase]={'requests':len(jobs),'estimated_cny':amount}
    assert sum(x['requests'] for x in phases.values())==684 and accounts=={'account_1'}
    plans={x['proposition_id']:x for x in c.pilot.jsonl(O/'plans_001/plans.jsonl')}
    fallbacks=Counter();used=Counter();whitespace_fixed=0
    for pid,entry in plans.items():
        raw=all_values['planner']['plan:'+pid]['native']; choice=raw['choices'][0];assert choice['finish_reason']=='stop'
        assert entry['output_text']==choice['message']['content'];assert len(json.loads(entry['output_text'])['queries'])==2
        try: parsed=pc.parse_plan(entry['output_text'],inputs[pid]);error=None
        except (ValueError,TypeError,KeyError,IndexError) as exc: parsed={'queries':[]};error=str(exc)
        assert entry['error']==error and entry['queries']==[q for q in parsed['queries'] if q!=inputs[pid]['text']]
        fallbacks[entry['status']]+=1
        if entry['status']=='valid_schema':used[inputs[pid]['author_type']]+=1
        if error=='Unverifiable source quote':
            obj=json.loads(entry['output_text']); item=copy.deepcopy(inputs[pid]); item['source']['local']=' '.join(item['source']['local'].split())
            for clue in obj['source_clues']:
                if isinstance(clue,dict) and isinstance(clue.get('quote'),str):clue['quote']=' '.join(clue['quote'].split())
            try:pc.parse_plan(json.dumps(obj),item);whitespace_fixed+=1
            except (ValueError,TypeError,KeyError,IndexError):pass
    assert fallbacks=={'valid_schema':100,'fallback_direct':44} and used=={'llm':65,'human':35} and whitespace_fixed==28
    vectors=bs.embedding_vectors();corpus=c.pilot.jsonl(P/'corpus.jsonl');passages={x['passage_id']:x for x in corpus}
    indices={sid:pc.HybridIndex([x for x in corpus if x['subject_id']==sid],[vectors[x['embedding_id']] for x in corpus if x['subject_id']==sid]) for sid in c.PATIENTS}
    candidates={x['proposition_id']:x for x in c.pilot.jsonl(O/'candidates_001/candidates.jsonl')}
    judge_inputs={x['proposition_id']:x for x in c.pilot.jsonl(O/'judge_preparation_001/inputs.jsonl')}
    for pid,x in inputs.items():
        row=candidates[pid];expected_queries=dict(direct=[x['text']],simple=list(dict.fromkeys([x['text'],x['source']['sentence'],x['source']['local']])),planner=list(dict.fromkeys([x['text']]+plans[pid]['queries'])))
        assert row['queries']==expected_queries
        ranks={}
        for query in dict.fromkeys(q for qs in row['queries'].values() for q in qs):
            ranks[query]=indices[x['subject_id']].retrieve(query,vectors[c.pilot.digest_text(query)])
            saved=next(r for r in row['query_rankings'] if r['query']==query)
            assert ranks[query]['hybrid']==saved['hybrid']
            for kind in ('bm25','dense'):assert [v[0] for v in ranks[query][kind]]==[v[0] for v in saved[kind]]
        for arm,queries in row['queries'].items():assert pc.candidate_pool([ranks[q]['hybrid'] for q in queries])==row['candidate_ids'][arm]
        val=all_values['rerank']['rerank:'+pid];job=val['job']; union=row['union_ids']
        assert job['body']['query']==x['text'] and job['passage_ids']==union
        assert job['body']['documents']==[passages[k]['search_text'] for k in union]
        scores={union[v['index']]:float(v['relevance_score']) for v in val['native']['results']}
        assert scores==judge_inputs[pid]['scores']
    raw_labels={}
    for rid,val in all_values['judge'].items():
        choice=val['native']['choices'][0];assert choice['finish_reason']=='stop';raw_labels[rid]=json.loads(choice['message']['content'])['verdict']
    assignments=c.pilot.read_csv(O/'judge_preparation_001/assignments.csv')[1]
    assert len(assignments)==432 and len({x['request_id'] for x in assignments})==299
    for a in assignments:
        b=all_values['judge'][a['request_id']]['job']['body'];assert c.pilot.fingerprint(b)==a['body_sha256']
        assert json.loads(b['messages'][1]['content'])==dict(proposition=inputs[a['proposition_id']]['text'],reference=judge_inputs[a['proposition_id']]['retrieval'][a['method']]['reference'])
    with redirect_stdout(io.StringIO()):score_results.score(T/'replay')
    same={f.name:h(f)==h(T/'replay'/f.name) for f in (U/'analysis').iterdir() if f.is_file() and f.name!='manifest.json'};assert all(same.values())
    for arm in c.METHODS:
        pred={x['proposition_id']:x['verdict'] for x in c.pilot.read_csv(T/'replay'/('predictions_'+arm+'.csv'))[1]}
        assert pred=={a['proposition_id']:raw_labels[a['request_id']] for a in assignments if a['method']==arm}
    gates=j(U/'diagnostics_001/case_candidate_gates.json');bycase={x['case_id']:x for x in candidates.values()}
    for gate in gates:
        row=bycase[gate['case_id']];span=next(x for x in corpus if x['note_id']==gate['note_id'] and x['start']==gate['passage_start'])
        ranking=row['query_rankings'][0];actual={}
        for k in ('bm25','dense','hybrid'):
            keys=ranking[k] if k=='hybrid' else [x[0] for x in ranking[k]];actual[k]=keys.index(span['passage_id'])+1 if span['passage_id'] in keys else None
        assert actual==gate['direct_query_ranks']
    assert all(h(R/n)==d for n,d in H['files_sha256'].items())
    metrics=j(T/'replay/metrics.json');summary=j(T/'replay/summary.json')
    result.update(status='limited_audit_checks_passed',phases=phases,estimated_total_cny=sum(x['estimated_cny'] for x in phases.values()),cohort=144,corpus_passages=len(corpus),plans=dict(fallbacks),used_by_author=dict(used),whitespace_only_rejections=whitespace_fixed,original_claim_only_rerank_verified=True,canonical_judge_jobs=299,repeat_jobs=12,repeat_label_changes=summary['repeat_label_changes'],score_files_identical=same,primary_delta={a:metrics[a]['contrasts']['planner_minus_direct']['metrics']['mcc'] for a in ('llm','human')},candidate_gate_cases=len(gates),all_submitted_files_unchanged=True,new_api_calls=0,finished_utc=datetime.now(timezone.utc).isoformat())
(T/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='score_files_identical'},ensure_ascii=False))
