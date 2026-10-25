from pathlib import Path
from collections import Counter
from decimal import Decimal as D
from datetime import datetime,timezone,timedelta
from contextlib import ExitStack,redirect_stdout
from unittest.mock import patch
import json,hashlib,sys,csv,io
R=Path('D:/Research-VeriFact'); O=R/'outputs/010_verifact_baseline_alignment'; T=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fp(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
h=read(O/'handoff_001.json'); assert all(sha(R/p)==d for p,d in h['files_sha256'].items())
e={'handoff_sha256':sha(O/'handoff_001.json'),'handoff_files':len(h['files_sha256']),'api_calls':0}
sys.path.insert(0,str(R/'tasks/010_verifact_baseline_alignment'))
import alignment_common as s
from sklearn.metrics import matthews_corrcoef,confusion_matrix
with ExitStack() as stack:
    for name in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
        stack.enter_context(patch(name,side_effect=AssertionError('Audit: network disabled')))
    base=O/'live/judge'; manifest=read(base/'manifest.json'); state=read(base/'state.json')
    assert fp(manifest)==state['run_id']; jobs={j['request_id']:j for j in manifest['jobs']}
    assert set(jobs)==set(state['jobs']) and len(jobs)==1324
    labels={}; statuses=Counter(); cost=D(0); reserve=D(0); starts=[]; exceptions=[]
    for rid,j in jobs.items():
        p=state['jobs'][rid];assert p['status']=='received' and len(p['receipts'])==p['attempts'] and not p.get('unreceipted_attempts')
        success=0
        for attempt,ptr in enumerate(p['receipts'],1):
            rec=read(base/ptr['file']); tr=rec['transport'];status=tr['http_status']; statuses[status]+=1;starts.append(tr['started_utc'])
            assert sha(base/ptr['file'])==ptr['sha256'] and rec['job_sha256']==fp(j) and rec['run_id']==state['run_id'] and rec['request_id']==rid and rec['attempt']==attempt
            if status==200:
                n=json.loads(tr['body_text']);u=n['usage'];ins,outs=u['prompt_tokens'],u['completion_tokens'];hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0))
                assert n['model']==s.CHAT_MODEL and n['choices'][0]['finish_reason']=='stop' and ins+outs==u['total_tokens']
                labels[rid]=json.loads(n['choices'][0]['message']['content'])['verdict'];success+=1
                hour=datetime.fromisoformat(tr['ended_utc']).astimezone(timezone(timedelta(hours=8))).hour
                amount=(D(ins-hit)*3+D(hit)*D('.3')+D(outs)*9)/D(1000000)*(D('.5') if 2<=hour<8 else D(1))
                assert attempt==p['attempts'];cost+=amount
            elif status==402:
                n=json.loads(tr['body_text']);assert n['code']==30001 and not n.get('choices');amount=D(0)
            else:
                assert status==0 and tr['outcome_unknown']
                amount=(D(len(json.dumps(j['body'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())+2000)*3+D(j['body']['max_tokens'])*9)/D(1000000)
                reserve+=amount; exceptions.append({'request_id':rid,'attempt':attempt,'reserved_cny':str(amount)})
            assert abs(amount-D(str(ptr['charge_cny'])))<D('1e-10')
        assert success==1
    assert len(list(base.glob('receipt_*.json')))==sum(statuses.values())==1329
    assert cost==D('23.3620932') and reserve==D('.105018') and abs(cost+reserve-D(str(state['used_or_reserved_cny'])))<D('1e-8') and cost+reserve<40
    assert read(O/'authority_001.json')['created_utc']<min(starts)
    e['receipts']={'statuses':dict(statuses),'usage_estimate_cny':str(cost),'unknown_reservation_cny':str(reserve),'unknown':exceptions,'one_success_per_job':True}
    cohort=rows(O/'preparation_001/cohort.csv');a=rows(O/'preparation_001/assignments.csv'); assert len(a)==1300
    assert (O/'preparation_001/cohort.csv').read_bytes()==(s.PRIOR/'preparation/cohort.csv').read_bytes()
    predictions={m:{} for m in s.METHODS}; bodyhashes=[]
    for x in a:
        predictions[x['arm']][x['proposition_id']]=labels[x['request_id']]
        assert fp(jobs[x['request_id']]['body'])==x['body_sha256'];bodyhashes.append(x['body_sha256'])
    assert len(set(bodyhashes))==1300
    for m in s.METHODS:assert predictions[m]=={x['proposition_id']:x['verdict'] for x in rows(O/'analysis_001'/('predictions_'+m+'.csv'))}
    release={p['proposition_id']:p['verdict'] for p in rows(O/'preparation_001/released_predictions.csv')}
    e['independent_metrics']={}
    for author in ('llm','human'):
        part=[r for r in cohort if r['author_type']==author]; gold=[r['human_gt'] for r in part]
        exported={r['proposition_id']:r['verdict'] for r in rows(R/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv')}
        assert all(release[r['proposition_id']]==exported[r['proposition_id']] for r in part)
        e['independent_metrics'][author]={}
        for m,pred in {**predictions,'release_system':release}.items():
            yp=[pred[r['proposition_id']] for r in part]
            e['independent_metrics'][author][m]={'n':len(part),'pa':sum(x==y for x,y in zip(gold,yp))/len(gold),'mcc':matthews_corrcoef(gold,yp),'confusion_S_NS_NA':confusion_matrix(gold,yp,labels=['Supported','Not Supported','Not Addressed']).tolist()}
    e['repeat_flips']=[r['case_id'] for r in read(O/'preparation_001/repeats.json') if labels[r['request_id']]!=labels[r['canonical_request_id']]]
    assert sorted(e['repeat_flips'])==['N103','N261']
    for r in read(O/'preparation_001/repeats.json'): assert jobs[r['request_id']]['body']==jobs[r['canonical_request_id']]['body']
    print('Independent receipt, cost, predictions and repetition checks passed',flush=True)
    path=R/'tasks/010_verifact_baseline_alignment/verify_alignment.py';text=path.read_text(encoding='utf-8')
    guard='assert output.is_relative_to(s.OUT) and not output.exists()';assert text.count(guard)==1
    scope={'__name__':'auditor_replay','__file__':str(path)}
    exec(compile(text.replace(guard,'assert not output.exists()'),str(path),'exec'),scope)
    with (T/'replay.log').open('w',encoding='utf-8') as log,redirect_stdout(log):scope['verify'](T/'replay')
    verification=read(T/'replay/verification.json');e['tests']=verification['tests'];e['replayed_files']=len(verification['replayed_content_sha256']);e['009_unchanged']=verification['historical_009_files_unchanged']
assert all(sha(R/p)==d for p,d in h['files_sha256'].items())
e['handoff_unchanged_after']=True
(T/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(e,ensure_ascii=False,indent=2),flush=True)
