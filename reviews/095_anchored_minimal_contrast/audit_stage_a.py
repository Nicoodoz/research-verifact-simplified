"""Independent, read-only stage A cache and live-ledger checks. No runner imports."""
from pathlib import Path
import json, hashlib, copy, sqlite3, datetime
from collections import Counter
R=Path(__file__).resolve().parents[2]
O=R/'outputs/095_anchored_minimal_contrast'
P=R/'.local_models/095'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def normalized(b):
    b=copy.deepcopy(b); m=b.pop('messages')
    assert len(m)==2 and [x['role'] for x in m]==['system','user']
    for k,v in [('n',1),('stream',False),('top_p',1)]: b.setdefault(k,v)
    return dict(parameters=b,system=m[0]['content'])
def unwrap(req):
    if isinstance(req.get('job'),dict): return req['job']['body']
    return req.get('body',req.get('request_body'))

def main():
    selected=rows(O/'cache_selected.jsonl'); candidates=rows(O/'cache_candidates.jsonl')
    inputs={x['proposition_id']:x for x in rows(R/'.local_models/092/inputs.jsonl')}
    reference={x['id']:x for x in rows(O/'reference_inventory.jsonl')}
    earliest={}
    for x in sorted(candidates,key=lambda r:(r['time'],r['request_path'],r['receipt_path'])): earliest.setdefault(x['id'],x)
    assert {x['id']:x for x in selected}==earliest
    assert len(inputs)==9065 and len(selected)==1885 and len(candidates)==2479
    for pid,x in inputs.items():
        assert digest(x['text'])==reference[pid]['claim_sha256']
        assert digest(x['reference'])==reference[pid]['reference_sha256']
    template=normalized(read(P/'judge_template.json'))
    # Verify every selected native request, not only an illustrative sample.
    checked=[]
    for x in selected:
        reqp=R/x['request_path']; recp=R/x['receipt_path']
        assert sha(reqp)==x['request_sha256'] and sha(recp)==x['receipt_sha256']
        b=unwrap(read(reqp)); assert normalized(b)==template
        assert digest(canon(b))==x['body_sha256']
        u=json.loads(b['messages'][1]['content']); i=inputs[x['id']]
        assert u=={'proposition':i['text'],'reference':i['reference']}
        rec=read(recp); tr=rec.get('transport',rec); native=json.loads(tr['body_text'])
        assert tr['http_status']==200 and native['model']=='deepseek-v4-flash-0731'
        checked.append(dict(id=x['id'],request_sha256=x['request_sha256'],receipt_sha256=x['receipt_sha256']))
    # Deterministic 40-case publicly reproducible audit list; content remains private.
    sample=sorted(checked,key=lambda x:digest('independent095/'+x['id']))[:40]
    jobs=rows(P/'baseline_jobs.jsonl')
    assert len(jobs)==7180 and len({j['request_id'] for j in jobs})==7180
    assert {j['id'] for j in jobs}==set(inputs)-set(earliest)
    assert [j['id'] for j in jobs]==sorted(set(inputs)-set(earliest),key=lambda s:digest('095/baseline/'+s))
    for j in jobs:
        b=j['body']; assert normalized(b)==template
        assert json.loads(b['messages'][1]['content'])=={'proposition':inputs[j['id']]['text'],'reference':inputs[j['id']]['reference']}
        bound=((len(canon(b).encode())+2000)*3+b['max_tokens']*9)/1e6
        assert abs(bound-j['bound_cny'])<1e-12
    for name in ['baseline_plan.json','runner_freeze.json']:
        for p,h in read(O/name)['sources'].items(): assert sha(R/p)==h
    # SQLite read-only snapshot: no calls to runner.db/reconcile and no mutations.
    con=sqlite3.connect('file:'+str(P/'budget.sqlite').replace('\\','/')+'?mode=ro',uri=True)
    con.execute('BEGIN'); ledger=con.execute('SELECT rid,num,phase,reserved,charge,status,folder FROM attempts').fetchall(); con.close()
    for rid,num,phase,reserved,charge,status,folder in ledger:
        r=read(R/folder/'request.json'); assert r['job']['request_id']==rid and r['attempt']==num
        assert r['prior_task_reserved']+reserved <= (150 if num>1 else 130)+1e-8
        assert charge<=reserved+1e-8
        if status==0: assert charge==reserved
        if status==200:
            tr=read(R/folder/'receipt.json')['transport']; n=json.loads(tr['body_text']); u=n['usage']
            cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
            expected=((u['prompt_tokens']-cached)*3+cached*.3+u['completion_tokens']*9)/1e6
            assert abs(charge-expected)<1e-10
    assert sum(x[4] for x in ledger)<=150
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Independent stage A cache identity, earliest-selection and live ledger snapshot; not final task audit',selected_native_requests_verified=len(checked),sample_40=sample,reference_bindings_verified=len(inputs),new_jobs_verified=len(jobs),cached_core_invalid_retained=sum(not r['parsed']['valid'] for r in selected),cached_raw_invalid_retained=sum(not r['parsed']['raw_valid'] for r in selected),snapshot_attempts=len(ledger),snapshot_status=dict(Counter(str(x[5]) for x in ledger)),snapshot_charge_or_reserve=sum(x[4] for x in ledger),status='PASS_WITH_SCOPE_LIMITS')
    out=Path(__file__).parent/'stage_a_checks.json'
    with out.open('x',encoding='utf-8',newline='\n') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print({k:v for k,v in result.items() if k!='sample_40'})
if __name__=='__main__': main()
