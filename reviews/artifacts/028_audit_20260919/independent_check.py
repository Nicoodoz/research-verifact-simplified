"""028 independent receipt, whitespace-only quote, accounting and frontier audit."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import sys,json,csv,hashlib,math,re,socket
import numpy as np
def blocked(*a,**k):raise RuntimeError('Offline audit')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
root=Path.cwd();out=Path(sys.argv[1]);base=root/'outputs/028_traceable_claim_evidence_verification';a=base/'analysis_001'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(v) for v in p.read_text(encoding='utf-8-sig').splitlines() if v]
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
history={}
for label in ['019_021','022','023','024','025','026','027']:history.update(read(root/f'reviews/artifacts/{label}_audit_20260919/audited_files_sha256.json'))
assert all(sha(root/p)==v for p,v in history.items())
jobs=jl(base/'preparation_001/jobs.jsonl');by={j['request_id']:j for j in jobs};materials={r['proposition_id']:r for r in jl(base/'preparation_001/materials.jsonl')};candidates={r['proposition_id']:r for r in read(base/'preparation_001/candidates.json')};norm={v['request_id']:v for v in jl(a/'normalized.jsonl')}
assert len(jobs)==310==len(by) and len(materials)==len(candidates)==155
assert [j['request_id'] for j in jobs]==[j['request_id'] for j in sorted(jobs,key=lambda j:hashlib.sha256(canonical('028/order/'+j['request_id']).encode()).hexdigest())]
class Pairs(list):pass
def plain(v):
    if isinstance(v,Pairs):
        d={}
        for k,x in v:
            x=plain(x);assert k not in d or canonical(d[k])==canonical(x);d[k]=x
        return d
    if isinstance(v,list):return [plain(x) for x in v]
    return v
def core(obj,key):
    vv=[plain(v) for k,v in obj if k==key];assert vv and all(canonical(v)==canonical(vv[0]) for v in vv);return vv[0]
def normalized(s):return ' '.join(s.split())
def located(quote,text):return bool(quote.strip()) and normalized(quote) in normalized(text)
terminal={};cost=defaultdict(Decimal);events=[];start=[];citations=invalid_citations=0;bad_cases=set();veto=[];relations=Counter();nrows=Counter()
for p in sorted((base/'attempts').glob('*/request.json')):
    q=read(p);rid=q['request_id'];j=by[rid];rec=read(p.parent/'receipt.json');tr=rec['transport']
    assert rid not in terminal and q['attempt']==1 and tr['http_status']==200
    assert q['body']==j['body'] and q['body_sha256']==hashlib.sha256(canonical(j['body']).encode()).hexdigest() and rec['request_sha256']==sha(p)
    payload=json.loads(q['body']['messages'][1]['content']);m=materials[j['proposition_id']]
    assert payload==dict(proposition=m['text'],reference=m['reference'])
    native=json.loads(tr['body_text']);assert native['model']=='deepseek-v4-flash-0731'
    u=native['usage'];assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens'];paid=Decimal(u['prompt_tokens']*3+u['completion_tokens']*9)/1000000;cost[j['arm']]+=paid
    reserve=Decimal((len(canonical(j['body']).encode())+2000)*3+4096*9)/1000000
    assert abs(float(reserve)-q['reservation_cny'])<1e-12 and q['prior_task_used_or_reserved_cny']+float(reserve)<=80
    assert q['created_utc']<=tr['started_utc']<=tr['ended_utc'];start.append(q['created_utc']);events.extend([(q['created_utc'],1,reserve),(tr['ended_utc'],0,paid-reserve)])
    obj=json.loads(native['choices'][0]['message']['content'],object_pairs_hook=Pairs)
    if j['arm']=='repeat':keep=core(obj,'verdict')=='Supported'
    else:
        coverage=core(obj,'claim_coverage');reqs=core(obj,'requirements');assert coverage in ['complete','uncertain'] and 1<=len(reqs)<=8
        nrows[len(reqs)]+=1;semantic=coverage=='complete';grounded=True
        parts=re.split(r'(?m)(?=^\d+\. Date:)',payload['reference']);entries={int(re.match(r'(\d+)\.',s).group(1)):s for s in parts if re.match(r'\d+\. Date:',s)}
        for rr in reqs:
            relations[rr['relation']]+=1;semantic&=rr['relation']=='supported'
            row_good=located(rr['claim_quote'],payload['proposition']) and bool(rr['evidence'])
            for e in rr['evidence']:
                citations+=1;ok=e['reference_id'] in entries and located(e['quote'],entries.get(e['reference_id'],''))
                invalid_citations+=not ok
                if not ok:bad_cases.add(j['proposition_id'])
                row_good&=ok
            grounded&=row_good
        keep=bool(semantic and grounded)
        if semantic and not grounded:veto.append(j['proposition_id'])
    assert keep==norm[rid]['keep'] and norm[rid]['status'] in ['valid','valid_with_format_anomaly']
    terminal[rid]=keep
assert len(terminal)==310
assert read(base/'preparation_001/manifest.json')['created_utc']<min(start)
balance=peak=Decimal(0)
for _,_,v in sorted(events):balance+=v;peak=max(peak,balance)
assert balance==Decimal('3.798027') and peak<80
assert citations==359 and invalid_citations==15 and len(bad_cases)==10 and len(veto)==4
assert all(candidates[p]['GT']=='Supported' for p in veto)
pred=csvr(a/'predictions.csv');lookup={(j['proposition_id'],j['arm']):terminal[j['request_id']] for j in jobs}
for r in pred:
    for arm in ['trace','repeat']:
        expected='Supported' if lookup.get((r['proposition_id'],arm),False) else r['U0']
        assert r[arm]==expected
assert len(pred)==1529 and len({r['subject_id'] for r in pred})==16
# Build the full three reference families without importing the study calculation.
old={r['proposition_id']:r['scores'] for r in jl(root/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if r['group']=='024_D'}
new={r['proposition_id']:r['scores'] for r in jl(root/'outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl') if r['model_key']=='deepseek' and r['arm']=='S'}
sc={**old,**new};curves=csvr(a/'curves.csv');saved=read(a/'matched.json');metrics=read(a/'metrics.json');labels=['Supported','Not Supported','Not Addressed']
def envelope(x,y,budget):
    x=np.asarray(x,float);y=np.asarray(y,float);best=max(y[x<=budget],default=0.)
    lo=np.where(x<budget)[0];hi=np.where(x>budget)[0]
    if len(lo) and len(hi):best=max(best,float((y[lo,None]+(budget-x[lo,None])/(x[None,hi]-x[lo,None])*(y[None,hi]-y[lo,None])).max()))
    return best
matched={}
for group in ['025','026','pooled']:
    rr=[r for r in pred if group=='pooled' or r['group']==group];subjects=sorted({r['subject_id'] for r in rr});sid=np.array([subjects.index(r['subject_id']) for r in rr]);y=np.array([r['GT']=='Supported' for r in rr]);u0=np.array([labels.index(r['U0']) for r in rr]);trace=np.array([labels.index(r['trace']) for r in rr])
    refs={};sd=[np.array([labels.index(r['SD']) for r in rr])];probs=[candidates[r['proposition_id']]['SD'] for r in rr if r['proposition_id'] in candidates]
    for threshold in [np.nextafter(max(probs),np.inf),*sorted(set(probs),reverse=True)]:
        sd.append(np.array([0 if r['proposition_id'] in candidates and candidates[r['proposition_id']]['SD']>=threshold else u0[i] for i,r in enumerate(rr)]))
    refs['SD']=np.array(sd);refs['repeat']=np.array([[labels.index(r[m]) for r in rr] for m in ['U0','repeat','U2']])
    times=[float(v['parameter']) for v in curves if v['group']==group and v['reference']=='global_lambda']
    refs['global_lambda']=np.array([[max([1,2,0],key=lambda k:math.log(max(sc[r['proposition_id']][labels[k]]/100,1e-6))+(lam if k==0 else 0)) for r in rr] for lam in times]);assert all(refs['global_lambda'][-1]==0)
    def counts(pp):
        changed=(np.atleast_2d(pp)==0)&(u0[None,:]!=0)
        return np.array([[sum(v&(sid==i)&y) for i in range(len(subjects))] for v in changed]),np.array([[sum(v&(sid==i)&~y) for i in range(len(subjects))] for v in changed])
    R,F=counts(trace);R,F=R[0],F[0];matched[group]={}
    for name,pp in refs.items():
        gR,gF=counts(pp);gain=sum(R)-envelope(gF.sum(1),gR.sum(1),sum(F))
        assert abs(gain-saved[group]['matched'][name]['R_gain_vs_mixture'])<1e-10
        draws=[]
        for seed in range(1000):
            w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects)),minlength=len(subjects));draws.append(R@w-envelope(gF@w,gR@w,F@w))
        ci=np.percentile(draws,[2.5,97.5]);np.testing.assert_allclose(ci,saved[group]['ci95'][name],atol=1e-10,rtol=0)
        for v in saved[group]['leave_one_patient_out']:
            w=np.array([s!=v['excluded_patient'] for s in subjects],int)
            assert abs(R@w-envelope(gF@w,gR@w,F@w)-v['comparisons'][name]['R_gain_vs_mixture'])<1e-10
        matched[group][name]=dict(gain=gain,ci95=ci.tolist())
# Case packets and all local quote anchors are source-bound.
ledger=read(base/'semantic_001/case_ledger.json');quote_count=0
for v in ledger:
    packet=read(base/'diagnosis_001'/(v['case_id']+'.json'));pid=v['proposition_id']
    assert packet['claim']==materials[pid]['text'] and packet['reference']==materials[pid]['reference']
    for arm in ['repeat','trace']:
        rid=next(j['request_id'] for j in jobs if j['proposition_id']==pid and j['arm']==arm)
        assert packet[arm]['output_text']==norm[rid]['output_text']
    for q in v['anchors']:assert packet['reference'][q['start']:q['end']]==q['quote'];quote_count+=1
result=dict(status='PASS',history_hashes=len(history),requests=310,valid=310,costs={k:str(v) for k,v in cost.items()},total_cny=str(balance),peak_reserved_cny=str(peak),citations=citations,invalid_citations=invalid_citations,citation_failure_cases=len(bad_cases),citation_only_veto_R=len(veto),requirements=sum(k*v for k,v in nrows.items()),requirements_distribution=dict(nrows),relation_counts=dict(relations),matched=matched,case_packets_bound=len(ledger),case_anchors=quote_count,network_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
