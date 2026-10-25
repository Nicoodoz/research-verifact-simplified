"""Auditor-written, receipt-only checks; never invokes an inference client."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from itertools import zip_longest
from unittest.mock import patch
from contextlib import ExitStack
import hashlib, json, csv, sys, re

ROOT=Path('D:/Research-VeriFact')
OUT=ROOT/'outputs/009_retrieval_baselines'
SCRATCH=Path(__file__).resolve().parent
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x]
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(x): return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def digest(x): return hashlib.sha256(x.encode()).hexdigest()
def emit(name,value):
    evidence[name]=value
    (SCRATCH/'independent_results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name, 'verified', flush=True)

evidence={'scope':'independent auditor checks, no inference API', 'network_disabled':True}
with ExitStack() as stack:
    for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
        stack.enter_context(patch(target,side_effect=AssertionError('Audit network disabled')))
    handoff=read(SCRATCH/'handoff.json')
    assert all(sha(ROOT/p)==h for p,h in handoff['files'].items())
    emit('handoff',{'sha256':sha(SCRATCH/'handoff.json'),'files_matched':len(handoff['files'])})
    groups=read(ROOT/'outputs/003_error_analysis/patient_groups.json')
    order=sorted(groups['groups']['development'],key=lambda p:digest(groups['seed']+p))
    protocol=read(OUT/'confirmation_protocol_001.json')
    assert protocol['patient_ids']==order[18:24]
    for p,h in protocol['implementation_sha256'].items(): assert sha(ROOT/p)==h
    assert sha(OUT/'development_001/analysis_001/manifest.json')==protocol['development_manifest_sha256']
    stages={}; phases={}; all_success={}; models=Counter(); errors=[]
    authority=read(OUT/'authority_001.json')
    for phase,cap in authority['stage_caps_cny'].items():
        base=OUT/'live'/phase
        manifest,state=read(base/'manifest.json'),read(base/'state.json')
        assert fp(manifest)==state['run_id']
        jobs={j['request_id']:j for j in manifest['jobs']}
        assert len(jobs)==len(manifest['jobs']) and set(jobs)==set(state['jobs'])
        cost=D(0); times=[]; hist=Counter(); kinds=Counter(); tokens=Counter(); attempts=0
        stage_values={}
        for rid,job in jobs.items():
            status=state['jobs'][rid]
            assert status['status']=='received' and not status.get('unreceipted_attempts')
            assert len(status['receipts'])==status['attempts']
            kinds[job['kind']]+=1
            own=[]
            for n,ptr in enumerate(status['receipts'],1):
                path=base/ptr['file']; rec=read(path); tr=rec['transport']; native=read_body=json.loads(tr['body_text'])
                assert sha(path)==ptr['sha256'] and rec['attempt']==n
                assert rec['request_id']==rid and rec['run_id']==state['run_id'] and rec['job_sha256']==fp(job)
                assert not tr.get('outcome_unknown') and tr['started_utc']<=tr['ended_utc']
                assert not own or own[-1][1]['ended_utc']<=tr['started_utc']
                http=tr['http_status']; hist[http]+=1; attempts+=1; times.append((tr['started_utc'],tr['ended_utc']))
                own.append((http,tr,rec))
                if http==402:
                    assert not native.get('choices') and not native.get('usage')
                    amount=D(0)
                    errors.append({'phase':phase,'request_id':rid,'attempt':n,'account':rec['account'],'code':native.get('code')})
                else:
                    assert http==200 and n==len(status['receipts'])
                    models[native.get('model',job['body']['model'])]+=1
                    if job['kind']=='chat':
                        u=native['usage']; ins=u['prompt_tokens']; outs=u['completion_tokens']; hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0))
                        assert ins+outs==u['total_tokens'] and 0<=hit<=ins
                        assert native['model']==job['body']['model']
                        assert len(native['choices'])==1 and native['choices'][0]['finish_reason']=='stop'
                        result=json.loads(native['choices'][0]['message']['content'])
                        assert result['verdict'] in {'Supported','Not Supported','Not Addressed'}
                        hour=datetime.fromisoformat(tr['ended_utc']).astimezone(timezone(timedelta(hours=8))).hour
                        factor=D('.5') if 2<=hour<8 else D(1)
                        amount=(D(ins-hit)*3+D(hit)*D('.3')+D(outs)*9)*factor/D(1000000)
                        tokens['prompt']+=ins; tokens['completion']+=outs; tokens['cached']+=hit
                    else:
                        u=native.get('usage',{}); count=u.get('prompt_tokens',u.get('total_tokens'))
                        if count is None: count=native.get('meta',{}).get('billed_units',{}).get('input_tokens')
                        if count is None: count=native.get('meta',{}).get('tokens',{}).get('input_tokens')
                        assert type(count) is int and count>0
                        amount=D(count)*D('.07')/D(1000000); tokens['provider_input']+=count
                    stage_values[rid]={'job':job,'response':native,'record':rec,'path':path}
                    all_success[rid]=stage_values[rid]
                assert abs(amount-D(str(ptr['charge_cny'])))<D('1e-12')
                cost+=amount
            assert sum(x[0]==200 for x in own)==1
            if len(own)>1:
                assert all(x[0]==402 for x in own[:-1])
                assert own[0][2]['account']!=own[-1][2]['account']
        assert set(base.glob('receipt_*.json'))=={base/p['file'] for x in state['jobs'].values() for p in x['receipts']}
        assert cost<=D(str(cap)) and abs(cost-D(str(state['used_or_reserved_cny'])))<D('1e-10')
        stages[phase]=stage_values
        phases[phase]={'jobs':len(jobs),'attempts':attempts,'status_counts':dict(hist),'kinds':dict(kinds),'tokens':dict(tokens),'cost_cny':str(cost),'first':min(t[0] for t in times),'last':max(t[1] for t in times)}
    total=sum(D(x['cost_cny']) for x in phases.values())
    assert total==D('18.08218167') and sum(x['jobs'] for x in phases.values())==2692 and sum(x['attempts'] for x in phases.values())==2700
    emit('receipt_accounting',{'phases':phases,'total_cny':str(total),'errors':errors,'models':dict(models),'estimated_not_invoice':True})
    assert authority['created_utc']<min(v['first'] for v in phases.values())
    assert protocol['created_utc']<min(phases[p]['first'] for p in phases if p.startswith('confirm'))
    assert phases['dev_judge']['last']<protocol['created_utc']
    assert phases['dev_rerank']['last']<phases['dev_embed']['first']<phases['dev_embed']['last']<phases['dev_judge']['first']
    assert read(OUT/'interventions_001/preparation/manifest.json')['created_utc']<phases['diagnostics']['first']
    emit('chronology',{'authority':authority['created_utc'],'confirmation_protocol':protocol['created_utc'],'development_refresh_before_judge':True,'diagnostic_preparation_before_calls':True})
    from sklearn.metrics import matthews_corrcoef, confusion_matrix
    results={}; data={}; labels=['Supported','Not Supported','Not Addressed']
    for folder,phase in [('development_001','dev_judge'),('confirmation_001','confirm_judge')]:
        base=OUT/folder; inputs=lines(base/'judge_preparation/inputs.jsonl'); cohort=rows(base/'preparation/cohort.csv')
        assert len({i['proposition_id'] for i in inputs})==len(inputs)==len(cohort)
        assert {i['subject_id'] for i in inputs}==set(order[12:18] if folder.startswith('development') else order[18:24])
        ci={r['proposition_id']:r for r in cohort}; pp={p['passage_id']:p for p in lines(base/'preparation/corpus.jsonl')}
        counts=Counter(); scores_missing=0; bodies={}; predictions={m:{r['proposition_id']:r['verdict'] for r in rows(base/'analysis_001'/('predictions_'+m+'.csv'))} for m in ('A48','B48','C48')}
        old_manifest=read(ROOT/'outputs/008_retrieval_planning/live/judge/manifest.json')
        old_jobs={j['request_id']:j for j in old_manifest['jobs']}
        old_state=read(ROOT/'outputs/008_retrieval_planning/live/judge/state.json')
        old_canonical={r['request_id'] for r in rows(ROOT/'outputs/008_retrieval_planning/judge_preparation_001/assignments.csv')}
        for i in inputs:
            assert ci[i['proposition_id']]['author_type']==i['author_type']
            ranked=i['rankings']; dense=[p for p,_ in ranked['dense']]; bm=[p for p,_ in ranked['bm25']]
            alternate=list(dict.fromkeys(p for pair in zip_longest(dense,bm) for p in pair if p is not None))[:48]
            for m,r in i['retrieval'].items():
                own=r['candidate_ids']; counts[m]+=1
                if m=='C48':
                    assert own==alternate and set(dense[:24]+bm[:24])<=set(own)
                elif m=='B48': assert own==dense[:48]
                elif m=='A48': assert own==ranked['hybrid'][:48]
                assert set(r['selected_ids'])<=set(own) and all(pp[p]['subject_id']==i['subject_id'] for p in own)
                rid=r['request_id']; bodyhash=r['body_sha256']
                if r['source']=='008':
                    assert folder=='development_001' and rid in old_canonical
                    job=old_jobs[rid]; ptr=old_state['jobs'][rid]['receipts'][-1]
                    native=json.loads(read(ROOT/'outputs/008_retrieval_planning/live/judge'/ptr['file'])['transport']['body_text'])
                else:
                    value=stages[phase][rid]; job=value['job']; native=value['response']
                assert fp(job['body'])==bodyhash
                assert json.loads(job['body']['messages'][1]['content'])=={'proposition':i['text'],'reference':r['reference']}
                assert bodyhash not in bodies or bodies[bodyhash]==rid
                bodies[bodyhash]=rid
                result=json.loads(native['choices'][0]['message']['content'])
                if m in predictions: assert predictions[m][i['proposition_id']]==result['verdict']
            value=stages['dev_embed' if folder.startswith('development') else 'confirm_rerank'][('dev_refresh:' if folder.startswith('development') else 'confirm_rerank:')+i['proposition_id']]
            job=value['job']; native=value['response']; pids=job['passage_ids']
            assert job['body']['query']==i['text'] and job['body']['documents']==[pp[p]['search_text'] for p in pids]
            pairs={pids[r['index']]:r['relevance_score'] for r in native['results']}
            assert len(pairs)==len(pids) and pairs==i['scores']
            union=set().union(*(set(r['candidate_ids']) for r in i['retrieval'].values()))
            assert set(pids)==union
        stats={}
        for author in ('llm','human'):
            ids=[r['proposition_id'] for r in cohort if r['author_type']==author]; y=[ci[p]['human_gt'] for p in ids]
            stats[author]={'n':len(ids),'gold_counts':dict(Counter(y)),'methods':{},'contrasts':{}}
            for m,pred in predictions.items():
                yp=[pred[p] for p in ids]
                stats[author]['methods'][m]={'pa':sum(a==b for a,b in zip(y,yp))/len(y),'mcc':matthews_corrcoef(y,yp),'confusion_S_NS_NA':confusion_matrix(y,yp,labels=labels).tolist()}
            for m in ('B48','C48'):
                transition=Counter('improved' if predictions[m][p]==ci[p]['human_gt'] and predictions['A48'][p]!=ci[p]['human_gt'] else 'worsened' if predictions[m][p]!=ci[p]['human_gt'] and predictions['A48'][p]==ci[p]['human_gt'] else 'changed_wrong' if predictions[m][p]!=predictions['A48'][p] else 'unchanged' for p in ids)
                stats[author]['contrasts'][m+'-A48']=dict(transition)
        results[folder]={'conditions':dict(counts),'distinct_bodies':len(bodies),'metrics':stats}
        data[folder]={'inputs':{x['case_id']:x for x in inputs},'passages':pp}
    emit('independent_predictions_candidates_scores',results)
    interventions=[]
    tab={x['case_id']:x for x in read(OUT/'interventions_001/analysis_001/case_results.json')}
    for case in read(OUT/'interventions_001/preparation/cases.json'):
        spec=case['spec']; item=data[spec['folder']]['inputs'][spec['case_id']]; pp=data[spec['folder']]['passages']
        recv=set(item['retrieval'][spec['receiver']]['selected_ids']); donor=set(item['retrieval'][spec['donor']]['selected_ids']); keys=set(case['keys']); ctrl=set(case['addition_control_ids']); removed=set(case['recipient_replaced_ids']); dc=set(case['donor_removal_control_ids'])
        assert keys<=donor and keys.isdisjoint(recv) and ctrl.isdisjoint(recv|donor) and removed<=recv and dc<=donor and dc.isdisjoint(keys)
        expected={'receiver_repeat':recv,'receiver_plus_key':(recv-removed)|keys,'receiver_plus_control':(recv-removed)|ctrl,'donor_repeat':donor,'donor_minus_key':donor-keys}
        if not case['donor_removal_control_missing']: expected['donor_minus_control']=donor-dc
        assert set(expected)==set(case['variants'])
        for mode,target in expected.items():
            v=case['variants'][mode]; assert set(v['selected_ids'])==target
            assert all(pp[k]['subject_id']==item['subject_id'] for k in target) and len(target)<=16 and v['body_characters']<=8000
            if v['source']=='new':
                response=stages['diagnostics'][v['request_id']]['response']
                result=json.loads(response['choices'][0]['message']['content'])
                assert result['verdict']==tab[spec['case_id']][mode]
            else: assert spec['case_id']=='N410' and mode=='receiver_plus_key'
        interventions.append({'case_id':spec['case_id'],'key_lengths':[len(pp[k]['text']) for k in keys],'addition_control_lengths':[len(pp[k]['text']) for k in ctrl],'donor_control_lengths':[len(pp[k]['text']) for k in dc],'shared_replacements':len(removed),'results':tab[spec['case_id']]})
    emit('intervention_transformations',interventions)
    drift=[]
    for i in lines(OUT/'development_001/preparation/inputs.jsonl'):
        for k in i['sentinel_ids']:
            v=stages['dev_rerank']['dev_rerank:'+i['proposition_id']]
            returned={v['job']['passage_ids'][r['index']]:r['relevance_score'] for r in v['response']['results']}
            drift.append(abs(i['cached_scores'][k]-returned[k]))
    ds=read(OUT/'rerank_drift_001/summary.json')
    assert len(drift)==ds['pairs']==12 and sum(d>1e-6 for d in drift)==ds['over_1e_6']==10 and max(drift)==ds['max_difference']
    repeats={}
    for folder,phase,seed in [('development_001','dev_judge','009/dev-diagnostic/v1:'),('confirmation_001','confirm_judge','009/confirm-repeat/v1:')]:
        items=list(data[folder]['inputs'].values()); groups=defaultdict(list)
        for i in items:groups[(i['subject_id'],i['author_type'])].append(i)
        expected={min(part,key=lambda i:digest(seed+i['proposition_id']))['proposition_id'] for part in groups.values()}
        saved=read(OUT/folder/'judge_preparation/repeats.json')
        assert {r['proposition_id'] for r in saved}==expected and len(saved)==12
        flips=[]
        for r in saved:
            repeated=stages[phase][r['request_id']]
            if folder.startswith('development'):
                canonical_body=old_jobs[r['canonical_request_id']]['body']
                ptr=old_state['jobs'][r['canonical_request_id']]['receipts'][-1]
                response=json.loads(read(ROOT/'outputs/008_retrieval_planning/live/judge'/ptr['file'])['transport']['body_text'])
            else:
                canonical=stages[phase][r['canonical_request_id']]
                canonical_body=canonical['job']['body']; response=canonical['response']
            assert repeated['job']['body']==canonical_body and fp(canonical_body)==r['body_sha256']
            a=json.loads(response['choices'][0]['message']['content'])['verdict']
            b=json.loads(repeated['response']['choices'][0]['message']['content'])['verdict']
            if a!=b:flips.append(r['case_id'])
        repeats[folder]={'pairs':12,'flips':flips}
    assert repeats['confirmation_001']['flips']==['N119']
    emit('drift_and_prespecified_repeats',{'bridge_pairs':12,'over_1e_6':10,'max_difference':max(drift),'repeats':repeats})
    assert all(sha(ROOT/p)==h for p,h in handoff['files'].items())
    emit('final_frozen_files_unchanged',len(handoff['files']))
print('INDEPENDENT CHECKS PASS',flush=True)
