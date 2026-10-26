"""Executor check from immutable inputs and native receipts; no model access."""
from collections import Counter
from decimal import Decimal
import json
import subprocess
import sys
import numpy as np
from sklearn.metrics import matthews_corrcoef, f1_score
import common098 as c
import runtime098 as rt
from verifact_research.evaluation import evaluate, paired_compare

def main():
    assert not (c.PRIVATE/'run.lock').exists()
    freeze=c.read(c.OUT/'execution_freeze.json')
    checks=0
    for rel,d in freeze['files'].items():assert c.sha(c.ROOT/rel)==d,rel;checks+=1
    jobs=c.lines(c.PRIVATE/'jobs.jsonl');cohort=c.lines(c.OUT/'cohort.jsonl');rows=c.lines(c.OUT/'predictions.jsonl')
    raw=c.lines(c.PRIVATE/'sample.jsonl');byid={r['id']:r for r in raw}
    assert len(byid)==len(raw)==len(rows)==len(cohort)==500;checks+=1
    assert not set(freeze['example_development_patients'])&set(freeze['evaluation_patients']);checks+=1
    inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    original={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
    for r in raw:
        x=original[r['id']];inp=inputs[r['id']]
        assert r['sid']==str(x['sid']) and r['GT']==x['GT'] and r['author']==x['author'] and x['historical_role']=='reserved_test'
        assert r['claim']==inp['text'] and r['C48']==inp['reference'] and r['Original']==x['original']
        assert c.digest(r['published_reference'])==r['published_reference_id'];checks+=3
    assert len({j['request_id'] for j in jobs})==len(jobs)==2120;checks+=1
    done=rt.completed();index={(j['id'],j['arm'],j['repeat']):j for j in jobs}
    for j in jobs:
        req=c.read(done[j['request_id']]/'request.json');rp=done[j['request_id']]/'receipt.json';rec=c.read(rp)
        assert req['job']==j and c.digest(c.canonical(j['body']))==j['body_sha256']
        assert rec['request_sha256']==c.sha(done[j['request_id']]/'request.json')
        r=byid[j['id']];payload=json.loads(j['body']['messages'][1]['content'].split('## Input JSON:\n')[-1])
        assert payload==dict(text=r['claim'],reference=r['C48'] if j['arm']=='C' else r['published_reference'])
        assert req['endpoint']==c.ENDPOINT
        assert req['prior_used_or_reserved_cny']+req['reservation_cny']<=req['operating_cap_cny']<=50
        assert req['reservation_cny']==j['busy_bound_cny'];checks+=6
        if j['repeat']:
            assert j['body']==index[j['id'],j['arm'],0]['body'];checks+=1
    for row in rows:
        for arm,pred in row['predictions'].items():
            if arm=='Original':continue
            j=index[row['id'],arm,0];tr=c.read(done[j['request_id']]/'receipt.json')['transport']
            assert pred==c.parse_native(tr)['verdict'];checks+=1
        for arm,pred in row['repeat_predictions'].items():
            j=index[row['id'],arm,1];tr=c.read(done[j['request_id']]/'receipt.json')['transport']
            assert pred==c.parse_native(tr)['verdict'];checks+=1
    # Decimal recomputation from original usage, independently of runtime float formula.
    con=rt.db();attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts').fetchall();con.close()
    total=Decimal(0);reserves=Decimal(0)
    for rid,n,arm,charge,status,folder in attempts:
        folder=c.ROOT/folder;req=c.read(folder/'request.json');tr=c.read(folder/'receipt.json')['transport']
        account=c.read(folder/'accounting.json')
        if account['basis'].startswith('usage'):
            response=json.loads(tr['body_text']);u=response['usage'];i=u['prompt_tokens'];o=u['completion_tokens'];cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
            factor=Decimal('.5') if account['basis']=='usage_idle' else Decimal(1)
            amount=(Decimal(i-cached)*3+Decimal(cached)*Decimal('.3')+Decimal(o)*9)/Decimal(1000000)*factor
        else:
            amount=Decimal(str(req['reservation_cny']));reserves+=amount
        assert abs(amount-Decimal(str(charge)))<Decimal('0.000000001');total+=amount;checks+=1
    cost=c.read(c.OUT/'cost_ledger.json')
    assert abs(total-Decimal(str(cost['used_or_reserved_cny'])))<Decimal('0.000000001') and total<=50;checks+=1
    a=c.read(c.OUT/'analysis.json');verified={}
    for panel,arms in [('natural',['O','C','P','Q']),('pressure',['O','P'])]:
        rr=[r for r in rows if r['panel']==panel and all(r['predictions'].get(x) in c.LABELS for x in arms)]
        cc=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr]
        for arm in ['Original']+arms:
            y=[r['GT'] for r in rr];p=[r['predictions'][arm] for r in rr]
            cm=np.array([[sum(yy==g and pp==z for yy,pp in zip(y,p)) for z in c.LABELS] for g in c.LABELS]);n=len(rr)
            rsum=cm.sum(1);psum=cm.sum(0);cor=int(np.trace(cm));den=np.sqrt((n*n-rsum@rsum)*(n*n-psum@psum));mcc=(cor*n-rsum@psum)/den if den else 0
            t=a['panels'][panel]['tables'][arm]
            assert cm.tolist()==t['confusion_matrix'] and cor==t['correct'] and int(cm[1:,0].sum())==t['false_S']
            assert abs(float(mcc)-t['mcc'])<1e-10 and abs(matthews_corrcoef(y,p)-t['mcc'])<1e-10
            assert abs(f1_score(y,p,labels=list(c.LABELS),average='macro',zero_division=0)-t['Macro_F1'])<1e-10;checks+=3
        for name,cmp in a['panels'][panel]['paired'].items():
            base=cmp['base'];candidate=cmp['candidate']
            p=lambda m:[dict(proposition_id=r['id'],verdict=r['predictions'][m]) for r in rr]
            again=paired_compare(cc,p(base),p(candidate),iterations=1000)
            assert again==cmp['paired'];checks+=1
        verified[panel]=dict(N=n,models=len(arms)+1)
    # All public generated files must be UTF-8 without BOM and omit clinical payloads/keys.
    secrets=[]
    for env in ['.env.aliyun','.env.siliconflow_pool']:
        for line in (c.ROOT/env).read_text(encoding='utf-8-sig').splitlines():
            k,sep,v=line.partition('=')
            if sep and ('KEY' in k.upper() or 'TOKEN' in k.upper()) and len(v.strip().strip('\"\''))>=12:
                secrets.append(v.strip().strip('\"\'').encode())
    forbidden={'claim','reference','published_reference','C48','body_text','reasoning_content','source_units'}
    def inspect(x):
        if isinstance(x,dict):
            assert not forbidden.intersection(x),forbidden.intersection(x)
            for v in x.values():inspect(v)
        elif isinstance(x,list):
            for v in x:inspect(v)
    for folder in [c.TASK,c.OUT]:
        for p in folder.rglob('*'):
            if not p.is_file():continue
            b=p.read_bytes();assert not b.startswith(b'\xef\xbb\xbf') and not any(s in b for s in secrets)
            if p.suffix=='.json':inspect(c.read(p))
            if p.suffix=='.jsonl':
                for x in c.lines(p):inspect(x)
            checks+=1
    result=dict(status='PASS',utc=c.utc(),checks=checks,verified_panels=verified,
                attempts=len(attempts),total_original_or_reserved_cny=str(total),unknown_reservation_cny=str(reserves),
                native_receipts_checked=len(jobs),patient_isolation=True,frozen_P_preserved=True,
                direct_verdict_only=True,default_changed=False,independent_audit=False,
                scope='Executor checks plus independent formulas/sklearn; not independent investigator or physician audit.')
    c.put(c.OUT/'selfcheck.json',result)
    print(c.canonical(result))

if __name__=='__main__':main()
