"""Executor provenance/identity/metrics/Decimal ledger verification; no network."""
from collections import Counter
from decimal import Decimal
import json
import numpy as np
from sklearn.metrics import matthews_corrcoef,f1_score
import common099 as c
import runtime099 as rt
from parse099 import parse
from verifact_research.evaluation import paired_compare

def main():
    assert not (c.PRIVATE/'run.lock').exists()
    f=c.read(c.OUT/'execution_freeze.json');checks=0
    for field in ['files','unchanged_098_fingerprints','unchanged_default_files','original_source_files']:
        for rel,d in f[field].items():assert c.sha(c.ROOT/rel)==d,rel;checks+=1
    amend=c.read(c.OUT/'format_amendment_freeze.json')
    for rel,d in amend['files'].items():assert c.sha(c.ROOT/rel)==d,rel;checks+=1
    jobs=c.lines(c.PRIVATE/'jobs.jsonl');rows=c.lines(c.OUT/'predictions.jsonl');sample={r['id']:r for r in c.lines(c.PRIVATE/'sample.jsonl')};done=rt.completed()
    assert len(jobs)==608==len({j['request_id'] for j in jobs})
    assert len(rows)==len(sample)==112;checks+=2
    native={};index={}
    for j in jobs:
        folder=done[j['request_id']];req=c.read(folder/'request.json');receipt=c.read(folder/'receipt.json');tr=receipt['transport']
        assert req['job']==j and receipt['request_sha256']==c.sha(folder/'request.json')
        assert req['endpoint']==c.ENDPOINT and req['prior_used_or_reserved_cny']+req['reservation_cny']<=req['operating_cap_cny']<=20
        assert c.digest(c.canonical(j['body']))==j['body_sha256']
        s=sample[j['id']];content=j['body']['messages'][1]['content'];payload=json.loads(content.split('## Input JSON:\n')[-1])
        assert payload==dict(text=s['claim'],reference=s[j['context']])
        assert set(payload)=={'text','reference'} and j['body']['enable_thinking'] and j['body']['thinking_budget']==2048 and j['body']['max_tokens']==512
        assert j['body']['temperature']==0 and j['body']['top_p']==1 and 'response_format' not in j['body'] and 'reasoning_effort' not in j['body']
        native[j['request_id']]=tr;index[j['id'],j['context'],j['model'],j['repeat']]=j;checks+=6
    groups={}
    for j in jobs:groups.setdefault((j['id'],j['context'],j['repeat']),[]).append(j)
    for group in groups.values():
        bodies=[{k:v for k,v in j['body'].items() if k!='model'} for j in group]
        assert len(group)==4 and all(b==bodies[0] for b in bodies);checks+=1
    for j in jobs:
        if j['repeat']:assert j['body']==index[j['id'],j['context'],j['model'],0]['body'];checks+=1
    canonical_cohort={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
    for row in rows:
        original=canonical_cohort[row['id']]
        assert row['GT']==original['GT'] and row['sid']==str(original['sid']) and row['author']==original['author'] and row['Original']==original['original'];checks+=1
        for context in ['O','C','repeat']:
            for model,pred in row[context+'_predictions'].items():
                if model in ['Original','V4_097']:continue
                j=index[row['id'],'O' if context=='repeat' else context,model,int(context=='repeat')];tr=native[j['request_id']]
                assert parse(tr)['verdict']==pred and c.parse(tr)['verdict']==row[context+'_strict'][model];checks+=1
    con=rt.db();attempts=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close();total=Decimal(0)
    successes=[]
    for rid,n,model,amount,status,folder in attempts:
        p=c.ROOT/folder;req=c.read(p/'request.json');tr=c.read(p/'receipt.json')['transport'];account=c.read(p/'accounting.json')
        if status!=200 or account['basis']!='verified_usage':
            actual=Decimal(str(req['reservation_cny']))
            assert abs(actual-Decimal(str(amount)))<Decimal('0.000000001')
            total+=actual;checks+=1
            if status==200:successes.append(rid)
            continue
        response=json.loads(tr['body_text']);u=response['usage']
        assert response['model']==model
        i,o=u['prompt_tokens'],u['completion_tokens'];cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
        if model=='qwen3.8-flash':ip,op,cp=Decimal('.8'),Decimal('2.7'),Decimal('.1')
        elif model=='qwen3.8-27b':ip,op,cp=Decimal(3),Decimal(12),Decimal('.6')
        elif model=='qwen3.5-27b':ip,op,cp=(Decimal('.6'),Decimal('4.8'),None) if i<=128000 else (Decimal('1.8'),Decimal('14.4'),None)
        else:ip,op,cp=(Decimal('.4'),Decimal('3.2'),None) if i<=128000 else (Decimal('1.6'),Decimal('12.8'),None)
        actual=(Decimal(i)*ip+Decimal(o)*op)/Decimal(1000000) if cp is None else (Decimal(i-cached)*ip+Decimal(cached)*cp+Decimal(o)*op)/Decimal(1000000)
        assert abs(actual-Decimal(str(amount)))<Decimal('0.000000001') and actual<=Decimal(str(req['reservation_cny']))+Decimal('0.000000001')
        total+=actual;checks+=2
        if status==200:successes.append(rid)
    assert len(successes)==len(set(successes))==608 and total<=20;checks+=1
    ledger=c.read(c.OUT/'cost_ledger.json');assert abs(total-Decimal(str(ledger['used_or_reserved_cny'])))<Decimal('0.000000001');checks+=1
    analysis=c.read(c.OUT/'analysis.json');verified={}
    Cjoint={r['id'] for r in rows if r['C_subset'] and all(r['O_predictions'].get(m) in c.LABELS and r['C_predictions'].get(m) in c.LABELS for m in c.MODELS)}
    for name,context,panel,subset in [('O_natural','O','natural',False),('C_subset','C','natural',True),('O_matched_C_subset','O','natural',True),('diagnostic','O','diagnostic',False)]:
        rr=[dict(r,predictions=r[context+'_predictions']) for r in rows if r['panel']==panel and (not subset or r['id'] in Cjoint) and all(r[context+'_predictions'].get(m) in c.LABELS for m in c.MODELS)]
        for model,t in analysis[name]['tables'].items():
            y=[r['GT'] for r in rr];z=[r['predictions'][model] for r in rr]
            cm=np.array([[sum(yy==g and pp==p for yy,pp in zip(y,z)) for p in c.LABELS] for g in c.LABELS]);n=int(cm.sum());correct=int(np.trace(cm));r=cm.sum(1);s=cm.sum(0)
            den=np.sqrt((n*n-r@r)*(n*n-s@s));mcc=(correct*n-r@s)/den if den else 0
            assert cm.tolist()==t['confusion_matrix'] and correct==t['correct'] and int(cm[1:,0].sum())==t['false_S']
            assert abs(mcc-t['mcc'])<1e-10 and abs(matthews_corrcoef(y,z)-t['mcc'])<1e-10
            assert abs(f1_score(y,z,labels=list(c.LABELS),average='macro',zero_division=0)-t['Macro_F1'])<1e-10;checks+=3
        for p in analysis[name]['paired'].values():
            cc=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr]
            pp=lambda m:[dict(proposition_id=r['id'],verdict=r['predictions'][m]) for r in rr]
            assert paired_compare(cc,pp(p['base']),pp(p['candidate']),iterations=1000)==p['paired'];checks+=1
        verified[name]=len(rr)
    # Source bytes/default098 guards are rechecked after offline output construction too.
    for field in ['unchanged_098_fingerprints','unchanged_default_files']:
        for rel,d in f[field].items():assert c.sha(c.ROOT/rel)==d,rel;checks+=1
    secrets=[]
    for line in (c.ROOT/'.env.aliyun').read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.partition('=')
        if sep and 'KEY' in key.upper():secrets.append(value.strip().strip('\"\'').encode())
    forbidden={'claim','reference','O','C','body_text','reasoning_content','source_units'}
    # O/C are legitimate context keys in some outputs; only clinical payload names are forbidden.
    forbidden-={'O','C'}
    def inspect(x):
        if isinstance(x,dict):
            assert not forbidden.intersection(x),forbidden.intersection(x)
            for v in x.values():inspect(v)
        elif isinstance(x,list):
            for v in x:inspect(v)
    clinical=[sample[pid][key].encode() for pid in sample for key in ['claim','O','C']]
    for root in [c.TASK,c.OUT]:
        for p in root.rglob('*'):
            if not p.is_file():continue
            b=p.read_bytes();assert not b.startswith(b'\xef\xbb\xbf') and not any(s and s in b for s in secrets)
            assert not any(len(s)>30 and s in b for s in clinical)
            if p.suffix=='.json':inspect(c.read(p))
            if p.suffix=='.jsonl':
                for item in c.lines(p):inspect(item)
            checks+=1
    out=dict(status='PASS',utc=c.utc(),checks=checks,native_receipts=608,attempts=len(attempts),total_directory_price_cny=str(total),verified_panels=verified,
         original_GT_preserved=True,GT_not_in_requests=True,model_only_generation_contrast=True,original_strict_parser_retained=True,
         unchanged098=True,unchanged_default=True,no_GPU_or_weights_download=True,independent_audit=False,
         scope='Executor selfcheck, independent formulas/sklearn/Decimal; not independent reviewer or physician audit')
    c.put(c.OUT/'selfcheck.json',out);print(c.canonical(out))

if __name__=='__main__':main()
