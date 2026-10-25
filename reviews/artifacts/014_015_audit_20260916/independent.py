from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal
from datetime import datetime, timedelta
import csv, json, hashlib, copy, sys

ROOT=Path('D:/Research-VeriFact'); TEMP=Path(__file__).resolve().parent
names={'014':'014_qwen27b_baseline_comparison','015':'015_disagreement_adjudication'}
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
rows=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
lines=lambda p:[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
canonical=lambda o:json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fp=lambda o:hashlib.sha256(canonical(o).encode()).hexdigest()
def output(receipt):
    d=json.loads(receipt['transport']['body_text'])
    assert len(d['choices'])==1 and d['choices'][0]['finish_reason']=='stop'
    a=json.loads(d['choices'][0]['message']['content'])
    assert a['verdict'] in ['Supported','Not Supported','Not Addressed']
    assert not d['choices'][0]['message'].get('reasoning_content')
    assert d['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0)==0
    return d,a

report={}; alljobs={}; answers={}
for n,name in names.items():
    o=ROOT/'outputs'/name; prep=read(o/'preparation_001/manifest.json')
    jobs=lines(o/'preparation_001/jobs.jsonl'); alljobs[n]=jobs
    jm={j['request_id']:j for j in jobs}; assert len(jm)==len(jobs)
    state=read(o/'live/state.json'); live=read(o/'live/manifest.json')
    assert state['run_id']==fp(live)
    assert live['preparation_sha256']==sha(o/'preparation_001/manifest.json')
    assert sha(o/'protocol_001.md')==prep['protocol_sha256']
    for section in ['files','dependencies','execution_code']:
        assert all(sha(ROOT/p)==h for p,h in prep[section].items())
    assert read(o/'authority_001.json')['created_utc']<=prep['created_utc']
    attempts=defaultdict(list); total=Decimal(0); reservation=Decimal(0); usage=Counter(); statuses=Counter(); ans={}; starts=[]
    for p in sorted((o/'live').glob('receipt_*.json')):
        r=read(p); t=r['transport']; j=jm[r['request_id']]
        assert r['run_id']==state['run_id'] and r['job_sha256']==fp(j)
        assert r['account']=='account_2'
        assert prep['created_utc']<t['started_utc']<=t['ended_utc']
        starts.append(t['started_utc']); statuses[str(t['http_status'])]+=1
        attempts[r['request_id']].append(r)
        ptr=next(x for x in state['jobs'][r['request_id']]['receipts'] if x['file']==p.name)
        assert sha(p)==ptr['sha256']
        if t['http_status']==200:
            d,a=output(r); assert d['model']==j['body']['model']
            assert r['request_id'] not in ans; ans[r['request_id']]=a
            u=d['usage']; pt=u['prompt_tokens']; ct=u['completion_tokens']
            assert u['total_tokens']==pt+ct and ct<=j['body']['max_tokens']
            usage.update(prompt_tokens=pt,completion_tokens=ct)
            if n=='014': charge=Decimal(pt*3+ct*12)/1000000
            else:
                hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0))
                assert 0<=hit<=pt
                local=datetime.fromisoformat(t['ended_utc'])+timedelta(hours=8)
                factor=Decimal('.5') if 2<=local.hour<8 else Decimal(1)
                charge=(Decimal(pt-hit)*3+Decimal(hit)*Decimal('.3')+Decimal(ct)*9)*factor/1000000
        else:
            assert n=='014' and t['http_status'] in [0,500]
            assert not t.get('body_text') or 'usage' not in json.loads(t['body_text'])
            charge=Decimal((len(canonical(j['body']).encode())+2000)*3+2048*12)/1000000
            reservation+=charge
        assert abs(charge-Decimal(str(ptr['charge_cny'])))<Decimal('1e-10')
        total+=charge
    for rid,rs in attempts.items():
        rs.sort(key=lambda r:r['attempt'])
        assert [r['attempt'] for r in rs]==list(range(1,len(rs)+1)) and len(rs)<=5
        assert rs[-1]['transport']['http_status']==200
        assert all(r['transport']['http_status']!=200 for r in rs[:-1])
        assert state['jobs'][rid]['status']=='received' and not state['jobs'][rid].get('unreceipted')
    assert set(ans)==set(jm)
    assert abs(total-Decimal(str(state['used_or_reserved_cny'])))<Decimal('1e-8') and total<40
    answers[n]=ans
    report[n]=dict(jobs=len(jobs),attempts=sum(statuses.values()),statuses=dict(statuses),usage=dict(usage),cost=float(total),unknown_reservation=float(reservation),prep=prep['created_utc'],first_start=min(starts),last_end=max(r['transport']['ended_utc'] for rs in attempts.values() for r in rs))

o14=ROOT/'outputs'/names['014']; o15=ROOT/'outputs'/names['015']
cohort=rows(o14/'preparation_001/cohort.csv'); assert (o14/'preparation_001/cohort.csv').read_bytes()==(o15/'preparation_001/cohort.csv').read_bytes()
g=read(ROOT/'outputs/003_error_analysis/patient_groups.json')
order=sorted(g['groups']['development'],key=lambda s:hashlib.sha256((g['seed']+s).encode()).hexdigest())
assert len(cohort)==650 and {r['subject_id'] for r in cohort}==set(order[18:24])
assert all(r['invalid']=='False' and r['proposition_type']=='claim' for r in cohort)
old=ROOT/'outputs/010_verifact_baseline_alignment'; oldjobs={j['request_id']:j for j in read(old/'live/judge/manifest.json')['jobs']}
oldassign={a['proposition_id']:a for a in rows(old/'preparation_001/assignments.csv') if a['arm']=='c48_reference'}
oldstate=read(old/'live/judge/state.json'); base={}; base_output={}; bodies={}
qwen={j['proposition_id']:answers['014'][j['request_id']]['verdict'] for j in alljobs['014']}
qoutput={j['proposition_id']:answers['014'][j['request_id']] for j in alljobs['014']}
for j in alljobs['014']:
    pid=j['proposition_id']; oj=oldjobs[oldassign[pid]['request_id']]; expected=copy.deepcopy(oj['body']);expected['model']='Qwen/Qwen3.8-27B'
    assert j['body']==expected
    rs=[read(old/'live/judge'/p['file']) for p in oldstate['jobs'][oj['request_id']]['receipts']]
    good=[r for r in rs if r['transport']['http_status']==200];assert len(good)==1
    assert good[0]['job_sha256']==fp(oj)
    d,a=output(good[0]);base[pid]=a['verdict'];base_output[pid]=a;bodies[pid]=oj['body']
dis={p for p in base if base[p]!=qwen[p]};assert len(dis)==78
preds={'v4':base,'qwen':qwen,'adjudication':dict(base),'evidence_only':dict(base)}
pairjobs=defaultdict(dict);order_diff=0;order_sources=Counter()
for j in alljobs['015']:
    pid=j['proposition_id'];assert pid in dis
    pairjobs[pid][j['arm']]=j
    payload=json.loads(j['body']['messages'][1]['content']);original=json.loads(bodies[pid]['messages'][1]['content'])
    assert {k:payload[k] for k in ['proposition','reference']}==original
    assert {k:v for k,v in j['body'].items() if k!='messages'}=={k:v for k,v in bodies[pid].items() if k!='messages'}
    if j['arm']=='adjudication':
        assert set(payload)=={'proposition','reference','candidate_judgments'}
        dg=hashlib.sha256(('015/candidate/v1:'+pid).encode()).hexdigest();vfirst=int(dg,16)%2==0
        order_diff+=vfirst!=(int(dg[0],16)%2==0);order_sources['v4' if vfirst else 'qwen']+=1
        expected=[base_output[pid],qoutput[pid]] if vfirst else [qoutput[pid],base_output[pid]]
        assert payload['candidate_judgments']==[dict(candidate='Candidate '+c,judgment=a) for c,a in zip('AB',expected)]
    else:assert set(payload)=={'proposition','reference'}
    preds[j['arm']][pid]=answers['015'][j['request_id']]['verdict']
for pid,js in pairjobs.items():
    a=copy.deepcopy(js['adjudication']['body']);b=js['evidence_only']['body'];p=json.loads(a['messages'][1]['content']);p.pop('candidate_judgments');a['messages'][1]['content']=canonical(p);assert a==b
assert order_diff==35
for name,pred in preds.items():
    assert pred=={r['proposition_id']:r['verdict'] for r in rows(o15/'analysis_001'/('predictions_'+name+'.csv'))}
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare
metrics15=read(o15/'analysis_001/metrics.json');pairs15=read(o15/'analysis_001/paired.json')
metrics14=read(o14/'analysis_001/metrics.json')
for author in ['llm','human']:
    cr=[r for r in cohort if r['author_type']==author];pp={k:[dict(proposition_id=r['proposition_id'],verdict=v[r['proposition_id']]) for r in cr] for k,v in preds.items()}
    for k,p in pp.items():assert evaluate(cr,p)==metrics15[author][k]
    assert metrics15[author]['v4']==metrics14[author]['v4_010'] and metrics15[author]['qwen']==metrics14[author]['qwen']
    for key,m in pairs15[author].items():
        new,old=key.split('_minus_');assert paired_compare(cr,pp[old],pp[new])==m
correct={k:sum(v[r['proposition_id']]==r['human_gt'] for r in cohort) for k,v in preds.items()}
report['results']=dict(correct=correct,disagreements=len(dis),order_deviation=order_diff,candidate_A=dict(order_sources),gate=read(o15/'analysis_001/gate.json')['winner'],metrics_and_intervals_match=True)
before=read(TEMP/'before.json');assert all(sha(ROOT/n)==h for n,h in before.items())
report['files_unchanged']=len(before)
(TEMP/'independent.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
