from pathlib import Path
from contextlib import ExitStack,redirect_stdout
from unittest.mock import patch
from collections import Counter
from datetime import datetime,timezone,timedelta
from decimal import Decimal as D
import json,csv,sys,hashlib
R=Path('D:/Research-VeriFact');O=R/'outputs/013_multi_mechanism_screen';T=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fp(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
h=read(O/'handoff_snapshot.json');assert all(sha(R/p)==v for p,v in h['files'].items())
e={'handoff_sha256':sha(O/'handoff_snapshot.json'),'handoff_files':len(h['files']),'new_api_calls':0}
sys.path.insert(0,str(R/'tasks/013_multi_mechanism_screen'));import study013 as s
with ExitStack() as st:
    for name in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):st.enter_context(patch(name,side_effect=AssertionError('No audit network')))
    phases={};all_values={};total=D(0);all_http=Counter()
    assert {p.name for p in (O/'live').iterdir() if p.is_dir()}=={'unit_aux','unit_judge','screen_aux','screen_judge'}
    for phase in ('unit_aux','unit_judge','screen_aux','screen_judge'):
        base=O/'live'/phase;m=read(base/'manifest.json');state=read(base/'state.json');assert fp(m)==state['run_id']
        jobs={j['request_id']:j for j in m['jobs']};assert set(jobs)==set(state['jobs'])
        cost=D(0);usage=D(0);reserve=D(0);http=Counter();kinds=Counter();times=[];values={}
        for rid,j in jobs.items():
            progress=state['jobs'][rid];assert progress['status']=='received' and len(progress['receipts'])==progress['attempts'] and not progress.get('unreceipted_attempts');n_ok=0;kinds[j['kind']]+=1
            for attempt,ptr in enumerate(progress['receipts'],1):
                path=base/ptr['file'];rec=read(path);tr=rec['transport'];code=tr['http_status'];http[code]+=1;times.append(tr['started_utc'])
                assert sha(path)==ptr['sha256'] and rec['request_id']==rid and rec['attempt']==attempt and rec['job_sha256']==fp(j) and rec['run_id']==state['run_id'] and rec['account']=='account_2'
                if code==200:
                    assert attempt==progress['attempts'];n_ok+=1;n=json.loads(tr['body_text'])
                    if j['kind']=='chat':
                        assert n['choices'][0]['finish_reason']=='stop' and n['model']==s.CHAT_MODEL
                        u=n['usage'];ins,outs=u['prompt_tokens'],u['completion_tokens'];hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0));assert ins+outs==u['total_tokens']
                        hour=datetime.fromisoformat(tr['ended_utc']).astimezone(timezone(timedelta(hours=8))).hour
                        amount=(D(ins-hit)*3+D(hit)*D('.3')+D(outs)*9)/D(1000000)*(D('.5') if 2<=hour<8 else D(1))
                    else:
                        u=n.get('usage',{});ins=u.get('prompt_tokens',u.get('total_tokens',n.get('meta',{}).get('billed_units',{}).get('input_tokens',n.get('meta',{}).get('tokens',{}).get('input_tokens'))));assert isinstance(ins,int)
                        amount=D(ins)*D('.07')/D(1000000)
                    usage+=amount;values[rid]={'job':j,'native':n}
                else:
                    assert code==0 and tr['outcome_unknown'] and j['kind']=='chat'
                    bodylen=len(json.dumps(j['body'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
                    amount=(D(bodylen+2000)*3+D(j['body']['max_tokens'])*9)/D(1000000);reserve+=amount
                assert abs(amount-D(str(ptr['charge_cny'])))<D('1e-10');cost+=amount
            assert n_ok==1
        assert len(list(base.glob('receipt_*.json')))==sum(http.values())
        assert abs(cost-D(str(state['used_or_reserved_cny'])))<D('1e-8') and cost<=D(str(s.STAGE_CAPS[phase]))
        phases[phase]={'requests':len(jobs),'http':dict(http),'kinds':dict(kinds),'usage_cost':str(usage),'reserved':str(reserve),'total':str(cost),'first':min(times)};total+=cost;all_http.update(http);all_values[phase]=values
    assert total==D('18.80024461') and sum(v['requests'] for v in phases.values())==1435 and sum(all_http.values())==1436
    for phase in phases:
        assert read(O/(phase+'_preparation_001')/'manifest.json')['created_utc']<phases[phase]['first']
    assert read(O/'authority_001.json')['protocol_sha256']==sha(O/'protocol_001.md')
    e.update(phases=phases,total_cny=str(total),http=dict(all_http))
    assignments=rows(O/'screen_judge_preparation_001/assignments.csv');assert len(assignments)==1398
    rawpred={};mainhashes=[]
    for a in assignments:
        v=all_values['screen_judge'][a['request_id']];assert fp(v['job']['body'])==a['body_sha256']
        label=json.loads(v['native']['choices'][0]['message']['content'])['verdict']
        if a['round']=='0':rawpred[(a['proposition_id'],a['arm'])]=label;mainhashes.append(a['body_sha256'])
    assert len(rawpred)==1386 and len(set(mainhashes))==930
    tr=rows(O/'screen_analysis_001/transitions.csv');assert len(tr)==231
    methods=['baseline','contract','text_guard','wide_candidates','selector','refresh48']
    assert all(r[m]==rawpred[(r['proposition_id'],m)] for r in tr for m in methods)
    nets={m:sum((r[m]==r['human_gt'])-(r['baseline']==r['human_gt']) for r in tr) for m in methods[1:]}
    assert nets=={'contract':-12,'text_guard':-4,'wide_candidates':-5,'selector':-5,'refresh48':-7}
    assert not read(O/'screen_analysis_001/gate.json')['eligible_methods']
    assert all(v['statistical_gate'] is False for v in read(O/'screen_analysis_001/mechanical_gates.json').values())
    e.update(independent_nets=nets,main_body_count=930,all_six_conditions_complete=True,no_combination_or_confirmation=True)
    print('Version, 1436 raw receipts, costs, canonical predictions and stop results independently verified',flush=True)
    source=R/'tasks/013_multi_mechanism_screen/verify013.py';text=source.read_text(encoding='utf-8');guard='assert not out.exists() and out.resolve().is_relative_to(s.OUT.resolve())';assert text.count(guard)==1
    scope={'__name__':'independent_audit_replay013','__file__':str(source)};exec(compile(text.replace(guard,'assert not out.exists()'),str(source),'exec'),scope)
    with (T/'replay.log').open('w',encoding='utf-8') as log,redirect_stdout(log):scope['verify'](T/'replay')
    e['replay']=read(T/'replay/verification.json')
assert all(sha(R/p)==v for p,v in h['files'].items());e['handoff_unchanged_after']=True
(T/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(e,ensure_ascii=False,indent=2),flush=True)
