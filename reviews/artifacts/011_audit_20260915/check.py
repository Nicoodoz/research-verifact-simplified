from pathlib import Path
from collections import Counter
from contextlib import ExitStack,redirect_stdout
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from decimal import Decimal as D
import sys,json,csv,hashlib
R=Path('D:/Research-VeriFact');O=R/'outputs/011_evidence_integrity_packaging';T=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fp(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
h=read(O/'handoff_001.json');assert all(sha(R/p)==v for p,v in h['files_sha256'].items())
sys.path.insert(0,str(R/'tasks/011_evidence_integrity_packaging'));import study011 as s
e={'head':s.BASE_HEAD,'handoff_sha256':sha(O/'handoff_001.json'),'handoff_files':len(h['files_sha256']),'new_api_calls':0}
with ExitStack() as stack:
    for name in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
        stack.enter_context(patch(name,side_effect=AssertionError('Audit forbids network')))
    base=O/'live/pilot';m=read(base/'manifest.json');state=read(base/'state.json');assert fp(m)==state['run_id']
    jobs={j['request_id']:j for j in m['jobs']};assert len(jobs)==195 and set(jobs)==set(state['jobs'])
    labels={};statuses=Counter();cost=D(0);starts=[];tokens=Counter()
    for rid,j in jobs.items():
        p=state['jobs'][rid];assert p['status']=='received' and not p.get('unreceipted_attempts') and len(p['receipts'])==p['attempts']
        count=0
        for n,ptr in enumerate(p['receipts'],1):
            rec=read(base/ptr['file']);tr=rec['transport'];native=json.loads(tr['body_text']);status=tr['http_status'];statuses[status]+=1;starts.append(tr['started_utc'])
            assert sha(base/ptr['file'])==ptr['sha256'] and rec['job_sha256']==fp(j) and rec['run_id']==state['run_id'] and rec['attempt']==n and rec['request_id']==rid and not tr.get('outcome_unknown')
            if status==402:assert native['code']==30001 and not native.get('choices');amount=D(0)
            else:
                assert status==200 and n==p['attempts'] and native['model']==s.CHAT_MODEL and native['choices'][0]['finish_reason']=='stop'
                count+=1;labels[rid]=json.loads(native['choices'][0]['message']['content'])['verdict'];u=native['usage'];ins,outs=u['prompt_tokens'],u['completion_tokens'];hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0))
                assert ins+outs==u['total_tokens'];hour=datetime.fromisoformat(tr['ended_utc']).astimezone(timezone(timedelta(hours=8))).hour
                amount=(D(ins-hit)*3+D(hit)*D('.3')+D(outs)*9)/D(1000000)*(D('.5') if 2<=hour<8 else D(1));tokens.update(input=ins,output=outs)
            assert abs(amount-D(str(ptr['charge_cny'])))<D('1e-10');cost+=amount
        assert count==1
    assert sum(statuses.values())==len(list(base.glob('receipt_*.json')))==199 and cost==D('1.2873834') and abs(cost-D(str(state['used_or_reserved_cny'])))<D('1e-10')
    auth=read(O/'authority_001.json');assert auth['created_utc']<min(starts)
    for name in ('offline_003','pilot_preparation_001','main_preparation_001'):
        assert read(O/name/'manifest.json')['created_utc']<min(starts)
    assert auth['protocol_sha256']==sha(O/'execution_protocol_001.md')
    for p,d in auth['immutable_source_sha256'].items():assert sha(R/p)==d
    assignments=rows(O/'pilot_preparation_001/assignments.csv');assert len(assignments)==216
    cohort={r['proposition_id']:r for r in rows(O/'offline_003/cohort.csv')};pred={}
    for a in assignments:
        assert a['request_id']==f"pilot:r{a['round']}:{a['body_sha256']}" and fp(jobs[a['request_id']]['body'])==a['body_sha256']
        key=(a['proposition_id'],int(a['round']));pred.setdefault(key,{})[a['arm']]=labels[a['request_id']]
    assert len(pred)==72 and len({p for p,r in pred})==24 and all(set(x)=={'A','B','C'} for x in pred.values())
    saved=rows(O/'pilot_analysis_001/predictions_and_transitions.csv')
    assert all(all(row[a]==pred[(row['proposition_id'],int(row['round']))][a] for a in s.METHODS) for row in saved)
    gate=read(O/'pilot_analysis_001/gate.json');nets={}
    for a,b in [('A','B'),('B','C')]:
        delta=[sum((v[b]==cohort[p]['human_gt'])-(v[a]==cohort[p]['human_gt']) for (p,r),v in pred.items() if r==i) for i in range(3)]
        nets[b+'-'+a]=delta;assert delta==gate['comparisons'][b+'_minus_'+a]['round_net_correct']
        assert sum(d>0 for d in delta)<2 and sum(delta)<3
    assert not gate['proceed_main'] and not (O/'live/main').exists()
    import native_stage011 as runner
    with patch.object(runner,'load_accounts',side_effect=AssertionError('Must stop before credentials')):
        try:runner.execute('main',O/'main_preparation_001/jobs.jsonl')
        except ValueError as ex:assert 'gate' in str(ex)
        else:raise AssertionError('Main was not blocked')
    e.update(receipts=dict(statuses),cost_cny=str(cost),tokens=dict(tokens),round_net_correct=nets,main_gate_rejected_before_credentials=True,protocol_and_inputs_precede_calls=True)
    print('Independent version, receipts, budget, repeat mapping and stop gate verified',flush=True)
    path=R/'tasks/011_evidence_integrity_packaging/verify011.py';text=path.read_text(encoding='utf-8');guard='assert out.is_relative_to(s.OUT) and not out.exists()';assert text.count(guard)==1
    scope={'__name__':'auditor_011_replay','__file__':str(path)};exec(compile(text.replace(guard,'assert not out.exists()'),str(path),'exec'),scope)
    with (T/'replay.log').open('w',encoding='utf-8') as log,redirect_stdout(log):scope['verify'](T/'replay')
    e['replay']=read(T/'replay/verification.json')
assert all(sha(R/p)==v for p,v in h['files_sha256'].items());e['handoff_unchanged_after']=True
(T/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(e,ensure_ascii=False,indent=2),flush=True)
