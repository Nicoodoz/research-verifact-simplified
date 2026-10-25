"""Alternative point-count and cost checks; executor verification, not independent audit."""
from collections import Counter
from decimal import Decimal
import csv, json, math
import numpy as np
from sklearn.metrics import matthews_corrcoef
import common019 as c

def load_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def independent_decision(q,lam):
    supported=max(q['Supported']/100,1e-6)*math.exp(lam)
    ns=max(q['Not Supported']/100,1e-6);na=max(q['Not Addressed']/100,1e-6)
    return 'Supported' if supported>max(ns,na) else 'Not Supported' if ns>=na else 'Not Addressed'

def basic_metrics(gt,pred):
    n=len(gt);counts=Counter(zip(gt,pred));correct=sum(g==p for g,p in zip(gt,pred))
    a=Counter(gt);b=Counter(pred)
    pooled=[(a[k]+b[k])/(2*n) for k in c.LABELS]
    chance=sum(x*(1-x) for x in pooled)/2
    return dict(correct=correct,percent_agreement=correct/n,gwet_ac1=(correct/n-chance)/(1-chance),
        mcc=float(matthews_corrcoef(gt,pred)),false_s=sum(g!='Supported' and p=='Supported' for g,p in zip(gt,pred)),
        confusion_matrix=[[counts[g,p] for p in c.LABELS] for g in c.LABELS])

def run():
    ledger=c.read(c.OUT/'live_ledger.json')
    c.require(not any(p['status']=='in_flight' for phase in ledger['phases'].values() for p in phase['jobs'].values()),'Wait for all in-flight requests')
    out=c.OUT/'recount_001';out.mkdir(exist_ok=False)
    metrics_checks=[];transitions=[];decode_checks=0;metarows=[]
    source={m['row']['proposition_id']:m['row'] for m in c.jsonlines(c.MATERIALS)}
    for stage in ('selection','validation'):
        folder=c.OUT/stage/'analysis_001'
        if not (folder/'metrics.json').exists():continue
        saved=c.read(folder/'metrics.json')
        norm={r['request_id']:r for r in c.jsonlines(folder/'normalized.jsonl')}
        assignments=load_csv(c.OUT/stage/'preparation/assignments.csv')
        logical={(r['proposition_id'],r['arm'],int(r['repeat'])):norm[r['request_id']] for r in assignments}
        for p in sorted(folder.glob('predictions_r*.csv')):
            rows=load_csv(p);rep=int(p.stem.split('_r')[-1]);arms=[k for k in rows[0] if k not in ('proposition_id','subject_id','author_type','human_gt')]
            for r in rows:
                original=source[r['proposition_id']]
                c.require(all(r[k]==str(original[k]) for k in ('human_gt','subject_id','author_type')),'Source identity or GT mismatch')
                for lam in c.GRID:
                    arm='U0' if lam==0 else f'U_lambda_{lam:g}'
                    expected=independent_decision(logical[(r['proposition_id'],'S',rep)]['scores'],lam)
                    c.require(expected==r[arm],'Alternative decoder mismatch');decode_checks+=1
                if rep==0:
                    flags={k:original.get(k) for k in ('invalid','proposition_type','time_metadata_conflict','second_round_anomaly','initial_agreement')}
                    metarows.append(dict(stage=stage,proposition_id=r['proposition_id'],**flags))
            for author in ('llm','human','all'):
                rr=[r for r in rows if author=='all' or r['author_type']==author]
                gt=[r['human_gt'] for r in rr]
                for arm in arms:
                    pred=[r[arm] for r in rr];v=basic_metrics(gt,pred);expected=saved[f'r{rep}/{author}/{arm}']
                    for k in ('percent_agreement','gwet_ac1','mcc'):c.require(abs(v[k]-expected[k])<1e-12,'Metric mismatch: '+k)
                    c.require(v['confusion_matrix']==expected['confusion_matrix'],'Confusion matrix mismatch')
                    metrics_checks.append(dict(stage=stage,repeat=rep,author=author,arm=arm,**v))
                    if arm in ('O','C_history','Always_S'):continue
                    base=[r['B'] for r in rr]
                    transitions.append(dict(stage=stage,repeat=rep,author=author,arm=arm,
                        rescued=sum(b!=g and n==g for g,b,n in zip(gt,base,pred)),
                        damaged=sum(b==g and n!=g for g,b,n in zip(gt,base,pred)),
                        gross_new_falseS=sum(g!='Supported' and b!='Supported' and n=='Supported' for g,b,n in zip(gt,base,pred)),
                        fixed_old_falseS=sum(g!='Supported' and b=='Supported' and n!='Supported' for g,b,n in zip(gt,base,pred)),
                        net_falseS_change=v['false_s']-basic_metrics(gt,base)['false_s'],
                        postprocessed_vs_raw_mismatch=sum(r[arm]!=r['V_raw'] for r in rr)))
    expected_fee=Decimal('0');attempts=0;http_counts=Counter();models=Counter();unknown_no_receipt=0
    for stage,phase in ledger['phases'].items():
        for rid,p in phase['jobs'].items():
            attempt_ids=[]
            for ptr in p['receipts']:
                path=c.OUT/ptr['file'];c.require(c.file_hash(path)==ptr['sha256'],'Receipt hash changed')
                r=c.read(path);tr=r['transport'];attempts+=1;http_counts[tr['http_status']]+=1;attempt_ids.append(r['attempt'])
                try:native=json.loads(tr['body_text'])
                except (ValueError,TypeError):native={}
                body=r['actual_body'];encoded=json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
                bound=((len(encoded)+2000)*3+body['max_tokens']*9)/1e6
                u=native.get('usage',{}) if isinstance(native,dict) else {}
                valid=type(u.get('prompt_tokens')) is int and type(u.get('completion_tokens')) is int
                if c.balance_exhausted(tr):fee=0.
                elif valid and u['prompt_tokens']>=0 and u['completion_tokens']>=0 and u.get('total_tokens',u['prompt_tokens']+u['completion_tokens'])==u['prompt_tokens']+u['completion_tokens']:
                    fee=(u['prompt_tokens']*3+u['completion_tokens']*9)/1e6
                else:fee=bound
                c.require(abs(fee-ptr['charge_cny'])<1e-12,'Receipt cost formula mismatch');expected_fee+=Decimal(str(fee))
                if tr['http_status']==200:models[native.get('model')]+=1
            for lost in p.get('unreceipted_attempts',[]):
                expected_fee+=Decimal(str(lost['reserved_cny']));unknown_no_receipt+=1;attempt_ids.append(lost['attempt'])
            c.require(len(attempt_ids)==len(set(attempt_ids))==p['attempts'],'Attempt count mismatch')
    c.require(abs(float(expected_fee)-ledger['used_or_reserved_cny'])<1e-8,'Cumulative budget mismatch')
    c.write_json(out/'checks.json',dict(executor_checks_only=True,independent_audit=False,decode_checks=decode_checks,metric_sets=len(metrics_checks),
        attempts_with_receipts=attempts,unreceipted_attempts=unknown_no_receipt,HTTP_status_counts=dict(http_counts),returned_models=dict(models),
        reconstructed_usage_plus_reserve_cny=float(expected_fee),ledger_usage_plus_reserve_cny=ledger['used_or_reserved_cny'],passed=True))
    c.write_csv(out/'metric_recounts.csv',metrics_checks);c.write_csv(out/'B_transition_events.csv',transitions);c.write_csv(out/'retained_cohort_metadata.csv',metarows)
    print(c.canonical(c.read(out/'checks.json')))

if __name__=='__main__':run()
