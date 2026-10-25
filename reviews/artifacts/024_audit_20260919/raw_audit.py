"""024 independent raw receipt, retry, accounting, parser and comparison audit; offline."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import sys,json,csv,math,hashlib,socket
def blocked(*a,**k):raise RuntimeError('Audit is offline')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
r=Path.cwd();out=Path(sys.argv[1]);base=r/'outputs/024_lambda2_transfer_validation'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x]
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
class Pairs(list):pass
def unique_value(obj,key):
    vals=[v for k,v in obj if k==key]
    assert vals,'Missing core'
    vals=[collapse(v) for v in vals]
    assert all(canonical(v)==canonical(vals[0]) for v in vals),'Conflicting core'
    return vals[0]
def collapse(v):
    if isinstance(v,Pairs):return {k:unique_value(v,k) for k,_ in v}
    if isinstance(v,list):return [collapse(x) for x in v]
    return v
history={}
for p in ['019_021','022','023']:
    folder=p+'_audit_20260919'
    history.update(read(r/'reviews/artifacts'/folder/'audited_files_sha256.json'))
assert all(sha(r/p)==h for p,h in history.items())
jobs=jl(base/'preparation_001/jobs.jsonl');byjob={j['request_id']:j for j in jobs}
norm={v['request_id']:v for v in jl(base/'analysis_001/normalized.jsonl')}
rows=csvr(base/'preparation_001/cohort.csv');truth={v['proposition_id']:v for v in rows}
dev=set(read(r/'outputs/003_error_analysis/patient_groups.json')['groups']['development'])
assert len(truth)==879 and all(str(v['subject_id']) in dev for v in rows)
assert len(jobs)==3516==len(byjob)==len(norm)
labels=['Supported','Not Supported','Not Addressed'];prices={'deepseek':(3,9),'qwen':(3,12)}
terminal={};perjob=defaultdict(list);events=[];counts=Counter();usage_total=Decimal(0);unknown=Decimal(0);anomalies=[]
for path in sorted((base/'attempts').glob('*/request.json')):
    q=read(path);rid=q['request_id'];j=byjob[rid]
    assert q['body']==j['body'] and q['endpoint']==read(base/'preparation_001/registry.json')['endpoint']
    assert hashlib.sha256(canonical(q['body']).encode()).hexdigest()==q['body_sha256']
    ip,op=prices[j['model_key']]
    reserve=Decimal((len(canonical(j['body']).encode())+2000)*ip+j['body']['max_tokens']*op)/1000000
    assert abs(float(reserve)-q['reservation_cny'])<1e-12
    assert q['prior_task_used_or_reserved_cny']+float(reserve)<=80+1e-10
    rp=path.parent/'receipt.json';assert rp.exists()
    rec=read(rp);assert rec['request_sha256']==sha(path)
    tr=rec['transport'];status=tr['http_status'];counts[status]+=1
    assert q['created_utc']<=tr['started_utc']<=tr['ended_utc']
    perjob[rid].append((q['attempt'],q['created_utc'],tr['ended_utc'],status))
    events.append((q['created_utc'],1,reserve))
    if status!=200:
        assert status==0 and tr['outcome_unknown'] and not tr['body_text']
        unknown+=reserve
        continue
    assert rid not in terminal
    native=json.loads(tr['body_text']);assert native['model']==j['body']['model']
    u=native['usage'];assert type(u['prompt_tokens']) is int and type(u['completion_tokens']) is int
    assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
    cost=Decimal(u['prompt_tokens']*ip+u['completion_tokens']*op)/1000000
    usage_total+=cost;events.append((tr['ended_utc'],0,cost-reserve))
    choice=native['choices'][0];content=choice['message']['content']
    # All actual responses are complete JSON; partial-JSON fallback is not needed in this run.
    obj=json.loads(content,object_pairs_hook=Pairs)
    assert isinstance(obj,Pairs)
    try:
        verdict=unique_value(obj,'verdict');assert verdict in labels
        scores=unique_value(obj,'label_scores') if j['arm']=='S' else None
        if scores is not None:
            assert set(scores)==set(labels) and all(type(v) is int and 0<=v<=100 for v in scores.values()) and sum(scores.values())==100
        parsed=dict(valid=True,verdict=verdict,scores=scores)
    except AssertionError:parsed=dict(valid=False,verdict=None,scores=None)
    n=norm[rid];assert parsed['valid']==(n['status'] in ('valid','valid_with_format_anomaly'))
    if parsed['valid']:assert parsed['verdict']==n['verdict'] and parsed['scores']==n['scores']
    if n['status']!='valid':
        anomalies.append(dict(request_id=rid,arm=j['arm'],model=j['model_key'],status=n['status'],errors=n['errors'],diagnostics=n['adherence'],finish_reason=choice['finish_reason']))
        if 'explanation_format_anomaly:reason' in n['adherence']:assert n['parsed']['reason'] is None
    terminal[rid]=parsed
for rid,attempts in perjob.items():
    aa=sorted(attempts);assert [x[0] for x in aa]==list(range(1,len(aa)+1)) and len(aa)<=3
    assert aa[-1][3]==200 and all(x[3]==0 for x in aa[:-1])
    assert all(a[2]<=b[1] for a,b in zip(aa,aa[1:]))
assert len(terminal)==3516 and counts==Counter({200:3516,0:104})
balance=peak=Decimal(0)
for _,_,delta in sorted(events):
    balance+=delta;peak=max(peak,balance)
assert balance==usage_total+unknown and peak<=80
assert usage_total==Decimal('50.876109') and unknown==Decimal('6.658335')
lookup={(j['model_key'],j['arm'],j['proposition_id']):terminal[j['request_id']] for j in jobs}
pred={m:{a:{} for a in ['B','V_raw','U0','U2']} for m in prices}
for m in prices:
    saved={v['proposition_id']:v for v in csvr(base/f'analysis_001/predictions_{m}.csv')}
    for pid in truth:
        b=lookup[(m,'B',pid)];s=lookup[(m,'S',pid)]
        p={'B':b['verdict'] if b['valid'] else None,'V_raw':s['verdict'] if s['valid'] else None}
        for name,lam in [('U0',0),('U2',2)]:
            p[name]=max(['Not Supported','Not Addressed','Supported'],key=lambda k:math.log(max(s['scores'][k]/100,1e-6))+(lam if k=='Supported' else 0)) if s['valid'] else None
        for a,v in p.items():pred[m][a][pid]=v;assert (saved[pid][a] or None)==v
paired=read(base/'analysis_001/paired.json');coh=read(base/'analysis_001/comparison_cohorts.json')
def totals(ids,p):
    cm=[[0]*3 for _ in labels]
    for pid in ids:cm[labels.index(truth[pid]['human_gt'])][labels.index(p[pid])]+=1
    n=len(ids);correct=sum(cm[i][i] for i in range(3));actual=[sum(x) for x in cm];predicted=[sum(cm[i][j] for i in range(3)) for j in range(3)]
    den=math.sqrt((n*n-sum(v*v for v in actual))*(n*n-sum(v*v for v in predicted)))
    mcc=(n*correct-sum(a*b for a,b in zip(actual,predicted)))/den if den else 0.
    return dict(n=n,correct=correct,false_s=cm[1][0]+cm[2][0],PA=correct/n,MCC=mcc,cm=cm)
for key,q in paired.items():
    m,author,comp=key.split('/')
    if m=='qwen-minus-deepseek':bp=pred['deepseek'][comp];cp=pred['qwen'][comp]
    else:cand,baseline=comp.split('-minus-');bp=pred[m][baseline];cp=pred[m][cand]
    full=[v['proposition_id'] for v in rows if author=='all' or v['author_type']==author]
    ids=[pid for pid in full if bp[pid] is not None and cp[pid] is not None]
    assert coh[key]['included_ids']==ids and coh[key]['excluded_ids']==[pid for pid in full if pid not in ids]
    bs=totals(ids,bp);cs=totals(ids,cp)
    assert cs['correct']-bs['correct']==q['net_correct']
    for side,v in [('baseline',bs),('candidate',cs)]:
        assert v['cm']==q[side]['confusion_matrix']
        assert abs(v['PA']-q[side]['percent_agreement'])<1e-12 and abs(v['MCC']-q[side]['mcc'])<1e-12
# Deterministic patient supplement is outside the main replay manifest; reconstruct its source deltas separately.
patient_changes=read(base/'analysis_001/paired_patient_changes.json')
for v in patient_changes:
    model=v['model'];cand,baseline=v['comparison'].split('-minus-')
    ids=coh[f"{model}/all/{v['comparison']}"]['included_ids']
    ids=[pid for pid in ids if truth[pid]['subject_id']==v['subject_id']]
    delta=sum(int(pred[model][cand][pid]==truth[pid]['human_gt'])-int(pred[model][baseline][pid]==truth[pid]['human_gt']) for pid in ids)
    assert len(ids)==v['n'] and delta==v['delta_correct']
assert len(patient_changes)==40
result=dict(status='PASS',history_hashes=len(history),requests=len(jobs),attempts=sum(counts.values()),http_counts=dict(counts),raw_complete_json=len(terminal),valid=sum(x['valid'] for x in terminal.values()),anomalous_or_invalid=anomalies,usage_cny=str(usage_total),unknown_reservation_cny=str(unknown),total_cny=str(balance),peak_reconstructed_reserved_cny=str(peak),comparison_count=len(paired),paired_patient_rows=len(patient_changes),network_blocked=True)
(out/'raw_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='anomalous_or_invalid'},indent=2))
