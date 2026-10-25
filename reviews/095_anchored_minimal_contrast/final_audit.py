"""Independent final audit: no paid runner imports, no API, no output mutation."""
import json,hashlib,math,datetime,sqlite3
from collections import Counter,defaultdict
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'outputs/095_anchored_minimal_contrast';P=R/'.local_models/095';D=Path(__file__).parent
L=['Supported','Not Supported','Not Addressed']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def close(x,y):assert abs(x-y)<1e-9,(x,y)
def metrics(rr,model):
    cm=[[0]*3 for _ in L]
    for r in rr:cm[L.index(r['GT'])][L.index(r['predictions'][model])]+=1
    n=len(rr);totr=[sum(x) for x in cm];totc=[sum(cm[i][j] for i in range(3)) for j in range(3)];correct=sum(cm[i][i] for i in range(3));pa=correct/n
    den=math.sqrt((n*n-sum(x*x for x in totr))*(n*n-sum(x*x for x in totc)))
    mcc=(n*correct-sum(a*b for a,b in zip(totr,totc)))/den if den else 0
    prec=[cm[i][i]/totc[i] if totc[i] else 0 for i in range(3)];rec=[cm[i][i]/totr[i] if totr[i] else 0 for i in range(3)];f1=[2*cm[i][i]/(totr[i]+totc[i]) if totr[i]+totc[i] else 0 for i in range(3)]
    avg=[(totr[i]+totc[i])/(2*n) for i in range(3)];pe=sum(v*(1-v) for v in avg)/2;fs=cm[1][0]+cm[2][0]
    return dict(N=n,correct=correct,PA=pa,MCC=mcc,AC1=(pa-pe)/(1-pe),Macro_F1=sum(f1)/3,precision=prec,recall=rec,F1=f1,confusion_matrix=cm,false_S=fs,true_non_S=sum(totr[1:]),predicted_S=totc[0],false_S_rate=fs/sum(totr[1:]) if sum(totr[1:]) else None,false_discovery_S=fs/totc[0] if totc[0] else None)
def metric_compare(actual,reported):
    for k,v in actual.items():
        if isinstance(v,list):
            if k=='confusion_matrix':assert v==reported[k]
            else:
                for a,b in zip(v,reported[k]):close(a,b)
        elif v is None:assert reported[k] is None
        else:close(v,reported[k])
def independent_prior(sc):
    ref=[1108/1378,100/1378,170/1378];cal=[48/143,47/143,48/143]
    z=[math.log(max(sc[k]/100,1e-6))+math.log(ref[i]/cal[i])+(0.1342909508820116 if i==0 else 0) for i,k in enumerate(L)]
    return L[max(range(3),key=z.__getitem__)]
def in_idle(tr):
    try:
        a=datetime.datetime.fromisoformat(tr['started_utc']);b=datetime.datetime.fromisoformat(tr['ended_utc']);zone=datetime.timezone(datetime.timedelta(hours=8))
        if a.tzinfo is None or b.tzinfo is None or not 0<=(b-a).total_seconds()<=3600:return False
        a=a.astimezone(zone);b=b.astimezone(zone)
        w=lambda x:x.date() if x.hour>=22 else x.date()-datetime.timedelta(days=1) if x.hour<8 else None
        return w(a) is not None and w(a)==w(b)
    except (ValueError,KeyError,TypeError):return False
def independent_charge(job,tr):
    bound=job['bound_cny']
    try:
        assert tr['http_status']==200 and tr.get('outcome_unknown') is not True
        n=json.loads(tr['body_text']);assert n['model']=='deepseek-v4-flash-0731';u=n['usage'];i=u['prompt_tokens'];o=u['completion_tokens'];cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        assert all(type(x)is int and x>=0 for x in [i,o,cached]) and cached<=i
        peak=((i-cached)*3+cached*.3+o*9)/1e6;assert peak<=bound+1e-8
        return peak*(.5 if in_idle(tr) else 1),True
    except (AssertionError,KeyError,TypeError,ValueError):return bound,False
def normalize(b):
    b=dict(b);m=b.pop('messages');assert len(m)==2
    for k,v in [('n',1),('stream',False),('top_p',1)]:b.setdefault(k,v)
    return {'parameters':b,'system':m[0]['content']}
def body(req):return req['job']['body'] if 'job' in req else req.get('body',req.get('request_body'))

def main():
    assert any(r['stage']=='analysis_ready' for r in rows(O/'progress.jsonl')),'Wait for final analysis_ready; do not audit partial results as final'
    assert not (P/'run.lock').exists()
    rr=rows(O/'unified_9065_predictions.jsonl');old={r['id']:r for r in rows(R/'outputs/092_task_adapted_verifier/oof_predictions.jsonl')};cohort={r['id']:r for r in rows(R/'outputs/092_task_adapted_verifier/cohort.jsonl')};inputs={r['proposition_id']:r for r in rows(R/'.local_models/092/inputs.jsonl')};template=normalize(read(P/'judge_template.json'))
    assert len(rr)==9065 and len({r['id'] for r in rr})==9065 and {r['id'] for r in rr}==set(old)==set(cohort)==set(inputs)
    invalid=[];core=[];raw=[];json_unreadable=[]
    for r in rr:
        pid=r['id'];z=old[pid];x=inputs[pid]
        for key in ['GT','sid','author','historical_role','time_metadata_conflict','initial_agreement','fold']:assert r[key]==z[key],(pid,key)
        assert r['GT']==cohort[pid]['GT'] and r['sid']==cohort[pid]['sid']
        for new,prior in [('Original','Original'),('092_Frozen','frozen'),('092_Finetuned','finetuned')]:assert r['predictions'][new]==z['predictions'][prior]
        assert r['claim_sha256']==digest(x['text']) and r['reference_sha256']==digest(x['reference']) and r['C48_source']==x['source']
        if not r['B_present']:assert r['B'] is None;continue
        v=r['B'];rq=R/v['request_path'];rp=R/v['receipt_path'];assert sha(rq)==v['request_sha256'] and sha(rp)==v['receipt_sha256']
        b=body(read(rq));assert normalize(b)==template
        assert json.loads(b['messages'][1]['content'])=={'proposition':x['text'],'reference':x['reference']}
        rec=read(rp);tr=rec.get('transport',rec);native=json.loads(tr['body_text']);assert tr['http_status']==200 and native['model']=='deepseek-v4-flash-0731'
        try:
            content=json.loads(native['choices'][0]['message']['content'])
            if content.get('verdict') in L:assert r['predictions']['B_raw']==content['verdict']
            if r['B_core_valid']:assert content['label_scores']==v['parsed']['scores']
        except (ValueError,TypeError):json_unreadable.append(pid)
        if r['B_raw_valid']:raw.append(r);assert r['predictions']['B_raw'] in L
        else:assert r['predictions']['B_raw'] is None
        if r['B_core_valid']:
            core.append(r);sc=v['parsed']['scores'];assert set(sc)==set(L) and sum(sc.values())==100 and all(type(s)is int and 0<=s<=100 for s in sc.values())
            assert r['predictions']['B_PriorG']==independent_prior(sc)
            z0=[math.log(max(sc[k]/100,1e-6)) for k in L];assert r['predictions']['B_U0']==L[max(range(3),key=z0.__getitem__)]
            z0[0]+=2;assert r['predictions']['B_U2']==L[max(range(3),key=z0.__getitem__)]
        else:invalid.append(pid);assert r['predictions']['B_PriorG'] is None
    reported=read(O/'baseline_metrics.json');independent={}
    for name,subset in [('full_9065_existing',rr),('common_core',core),('common_raw',raw)]:
        independent[name]={}
        for model in reported[name]:
            actual=metrics(subset,model);metric_compare(actual,reported[name][model]);independent[name][model]=actual
    cov=read(O/'baseline_coverage.json');assert cov['universe']==len(rr) and cov['core_valid_B']==len(core) and cov['raw_valid_B']==len(raw) and cov['HTTP200_core_invalid']==len(invalid)
    assert cov['missing']==sum(not r['B_present'] for r in rr) and cov['successful_B']==sum(r['B_present'] for r in rr)
    paired=read(O/'baseline_paired.json')
    for name,z in paired.items():
        subset=raw if name=='raw_B-Original' else core;base=z['base'];candidate=z['candidate'];patients=defaultdict(lambda:[0,0]);rescue=Counter();harm=Counter();added=avoided=0
        for r in subset:
            g=r['GT'];a=r['predictions'][base];b=r['predictions'][candidate];p=patients[r['sid']]
            if a!=g and b==g:rescue[g]+=1;p[0]+=1
            if a==g and b!=g:harm[g]+=1;p[1]+=1
            added+=g!=L[0] and a!=L[0] and b==L[0];avoided+=g!=L[0] and a==L[0] and b!=L[0]
        assert sum(rescue.values())==z['rescue'] and sum(harm.values())==z['harm'] and z['net']==sum(rescue.values())-sum(harm.values())
        assert added==z['false_S_added'] and avoided==z['false_S_prevented']
        nets={str(k):v[0]-v[1] for k,v in patients.items()};assert nets==z['patient_net']
        assert [sum(v>0 for v in nets.values()),sum(v<0 for v in nets.values()),sum(v==0 for v in nets.values())]==z['patient_win_loss_tie']
    ledger=rows(O/'attempt_ledger.jsonl');cost=read(O/'cost_ledger.json');total=unknown=0.;phases=Counter();successful=[];arms=Counter();known_count=0
    for a in ledger:
        request=read(R/a['request_path']);j=request['job'];tr=read(R/a['receipt_path'])['transport'] if a['receipt_path'] else None
        assert sha(R/a['request_path'])==a['request_sha256']
        if tr:assert sha(R/a['receipt_path'])==a['receipt_sha256']
        assert digest(canonical(j['body']))==j['body_sha256']==a['body_sha256']
        value,known=independent_charge(j,tr);close(value,a['charge_or_reserved_cny']);assert known==a['billing_usage_known'];total+=value;unknown+=value if not known else 0;known_count+=known;phases[j['phase']]+=value;arms[j['arm']]+=1
        bound=j['bound_cny'];assert request['prior_task_reserved']+bound<=(150 if a['attempt']>1 else 130)+1e-8
        cap={'baseline':80,'baseline_completion':25,'method':45,'extension':35,'preflight':1}[j['phase']];assert request['prior_phase_reserved']+bound<=cap+1e-8
        if tr and tr['http_status']==200:
            successful.append((j['id'],j['body_sha256'],j['arm']));payload=json.loads(j['body']['messages'][1]['content']);pid=j['id'];x=inputs[pid]
            assert not set(payload)&{'GT','human_gt','original','B_raw','B_G','label','verdict'}
            if j['arm']=='B':assert payload=={'proposition':x['text'],'reference':x['reference']}
            elif j['arm']=='construct':assert payload=={'claim':x['text'],'reference':x['reference']}
            elif j['arm']=='check':assert payload['original_claim']==x['text'] and payload['reference']==x['reference']
            else:raise AssertionError(('unexpected final candidate call',j['arm']))
    close(total,cost['total_directory_price_or_unknown_cny']);close(unknown,cost['unknown_reserve_cny']);assert total<=150 and len(ledger)==cost['attempts']
    assert len(successful)==len(set(successful))==cost['HTTP200'];assert arms['E']==arms['C']==0
    for phase,v in phases.items():close(v,cost['phase_costs'][phase])
    con=sqlite3.connect('file:'+str(P/'budget.sqlite').replace('\\','/')+'?mode=ro',uri=True);n,dbtotal=con.execute('SELECT COUNT(*),SUM(charge) FROM attempts').fetchone();con.close();assert n==len(ledger);close(total,dbtotal)
    stop=read(O/'construction_stop.json');assert stop['decision']=='STOP_C_FINAL_JUDGE_CONTINUE_A_F'
    checked=rows(P/'checked.jsonl');assert len(checked)==300 and sum(x['operated'] for x in checked)==95
    out=dict(status='PASS independent final numeric/source/accounting scope; written prose and nonstandard JSON exceptions separately reviewed',N=len(rr),patients=len({r['sid'] for r in rr}),core_N=len(core),raw_N=len(raw),invalid_IDs=invalid,nonstandard_JSON_IDs=json_unreadable,metrics=independent,attempts=len(ledger),HTTP200=len(successful),phase_costs=dict(phases),cost_or_unknown_cny=total,unknown_cny=unknown,known_usage_attempts=known_count,arms_attempts=dict(arms),candidate_final_calls=0,all_selected_B_native_source_verified=True,GT_payload_whitelist_verified=True,unique_success_ID_body_arm=True,artifact_hashes={f:sha(O/f) for f in ['unified_9065_predictions.jsonl','baseline_metrics.json','baseline_paired.json','cost_ledger.json','attempt_ledger.jsonl']})
    with (D/'final_checks.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print({k:v for k,v in out.items() if k not in ['metrics','invalid_IDs','nonstandard_JSON_IDs','artifact_hashes']})
if __name__=='__main__':main()
