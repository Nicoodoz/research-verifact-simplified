"""Frozen A same-ID evaluation, without result-conditioned selection."""
import csv, json, sqlite3, sys, statistics
from collections import Counter
import common097 as c
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
import core024
sys.path.insert(0,str(c.ROOT/'tasks/090_demo_constructor_repair_validation'))
from analyze090 import parse_arm
sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from metrics095 import score,paired

ARMS=['published_B','C48_native','published_native']
def native_label(tr):
    try:
        response=json.loads(tr['body_text']);choice=response['choices'][0]
        content=choice['message'].get('content')
        obj=core024.loads(content)
        assert isinstance(obj,core024.Object)
        verdict=core024.unique(obj,'verdict')
        assert verdict in c.LABELS
        try:reason=core024.unique(obj,'reason')
        except (ValueError,TypeError):reason=None
        return verdict,dict(raw_valid=True,reason_present=isinstance(reason,str) and bool(reason.strip()),finish_reason=choice.get('finish_reason'),usage=response.get('usage',{}),status='valid' if isinstance(reason,str) and bool(reason.strip()) and choice.get('finish_reason')=='stop' else 'format_anomaly')
    except (ValueError,TypeError,KeyError,IndexError,AssertionError,AttributeError):
        response=json.loads(tr['body_text']);return None,dict(raw_valid=False,reason_present=False,finish_reason=response.get('choices',[{}])[0].get('finish_reason'),usage=response.get('usage',{}),status='invalid_final_json_or_verdict')
def main():
    assert not (c.PRIVATE/'run.lock').exists(),'active requests must finish before evaluation'
    freeze=c.read(c.OUT/'a_execution_freeze.json');assert c.sha(c.OUT/'a_execution_panel.jsonl')==freeze['panel_sha256']
    panel=c.lines(c.OUT/'a_execution_panel.jsonl');jobs=c.lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl')
    assert len(panel)==160 and len(jobs)==480
    con=sqlite3.connect(c.PRIVATE/'budget.sqlite')
    attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rid,num').fetchall();con.close()
    success={}
    ledger=[]
    for rid,num,arm,charge,status,folder in attempts:
        rp=c.ROOT/folder/'receipt.json';req=c.ROOT/folder/'request.json';tr=c.read(rp)['transport'] if rp.exists() else None
        x=dict(request_id=rid,attempt=num,arm=arm,cost_or_reserved_cny=charge,http_status=status,request_sha256=c.sha(req),receipt_sha256=c.sha(rp) if rp.exists() else None,folder=folder)
        ledger.append(x)
        if status==200:
            assert rid not in success
            success[rid]=(tr,x)
    jobby={(j['id'],j['arm']):j for j in jobs};rows=[];invalid=Counter();tokens={a:[] for a in ARMS};costs=Counter()
    for x in ledger:costs[x['arm']]+=x['cost_or_reserved_cny']
    for base in panel:
        row={k:base[k] for k in ['id','sid','author','GT','C48_sha256','published_reference_id','published_verdict','C48_chars','published_chars']}
        row['predictions']=dict(Original=base['published_verdict'],C48_B_raw=base['B_raw'],C48_B_PriorG=base['B_PriorG'])
        row['arms']={}
        for arm in ARMS:
            job=jobby[base['id'],arm]
            if job['request_id'] not in success:
                invalid[arm+'_missing']+=1;row['predictions'][arm]=None;row['arms'][arm]=dict(status='missing',request_id=job['request_id']);continue
            tr,led=success[job['request_id']]
            if arm=='published_B':
                parsed,labels=parse_arm(tr,None)
                pred=labels['raw'];secondary=labels['PriorG'] if parsed['valid'] else None
                row['predictions']['published_B_PriorG']=secondary
                info=dict(status=parsed['status'],raw_valid=parsed['raw_valid'],score_valid=parsed['scores_valid'],core_valid=parsed['valid'],finish_reason=parsed['finish_reason'],usage=parsed['usage'])
            else:pred,info=native_label(tr)
            info.update(request_id=job['request_id'],body_sha256=job['body_sha256'],receipt_sha256=led['receipt_sha256'])
            if pred is None:invalid[arm+'_raw_invalid']+=1
            row['predictions'][arm]=pred;row['arms'][arm]=info
            if info.get('usage'):tokens[arm].append(info['usage'])
        rows.append(row)
    c.write_lines(c.OUT/'a_same_id.jsonl',rows)
    columns=['id','sid','author','GT','Original','C48_B_raw','published_B','C48_native','published_native','C48_B_PriorG','published_B_PriorG','C48_chars','published_chars','C48_sha256','published_reference_id','published_B_raw_valid','published_B_score_valid','C48_native_raw_valid','published_native_raw_valid']
    csv_path=c.OUT/'a_same_id.csv'
    with csv_path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');writer.writeheader()
        for r in rows:
            flat={k:r.get(k) for k in ['id','sid','author','GT','C48_chars','published_chars','C48_sha256','published_reference_id']}
            flat.update(r['predictions'])
            for arm in ARMS:
                flat[arm+'_raw_valid']=r['arms'][arm].get('raw_valid',False)
            flat['published_B_score_valid']=r['arms']['published_B'].get('score_valid',False)
            writer.writerow(flat)
    c.write_lines(c.OUT/'a_request_ledger.jsonl',ledger)
    raw=[r for r in rows if all(r['predictions'].get(a) in c.LABELS for a in ('C48_B_raw','C48_B_PriorG',*ARMS))]
    models=['Original','C48_B_raw','published_B','C48_native','published_native','C48_B_PriorG']
    tables=score(raw,models) if raw else {}
    comparisons={}
    for base,candidate in [('C48_B_raw','C48_native'),('published_B','published_native'),('C48_B_raw','published_B'),('C48_native','published_native'),('C48_B_PriorG','C48_native'),('C48_B_PriorG','published_native')]:
        if raw:comparisons[candidate+'__vs__'+base]=paired(raw,base,candidate)
    core=[r for r in raw if r['predictions'].get('published_B_PriorG') in c.LABELS]
    secondary=score(core,['Original','C48_B_raw','C48_B_PriorG','published_B','published_B_PriorG','C48_native','published_native']) if core else {}
    patient={sid:score([r for r in raw if r['sid']==sid],models) for sid in sorted({r['sid'] for r in raw})} if raw else {}
    author={name:score([r for r in raw if r['author']==name],models) for name in sorted({r['author'] for r in raw})} if raw else {}
    transitions={key:[dict(GT=g,base=b,candidate=n,count=v) for (g,b,n),v in sorted(Counter((r['GT'],r['predictions'][base],r['predictions'][candidate]) for r in raw).items())] for key,base,candidate in [('native_C48','C48_B_raw','C48_native'),('native_published','published_B','published_native'),('reference_B','C48_B_raw','published_B'),('reference_native','C48_native','published_native')]}
    usage={arm:dict(N=len(us),prompt_tokens=sum(u['prompt_tokens'] for u in us),completion_tokens=sum(u['completion_tokens'] for u in us),prompt_mean=statistics.mean(u['prompt_tokens'] for u in us) if us else None,completion_mean=statistics.mean(u['completion_tokens'] for u in us) if us else None) for arm,us in tokens.items()}
    allmodels=['Original','C48_B_raw','C48_B_PriorG','published_B','C48_native','published_native','published_B_PriorG']
    full_coverage={m:dict(valid=sum(r['predictions'].get(m) in c.LABELS for r in rows),correct_lower_bound=sum(r['predictions'].get(m)==r['GT'] for r in rows),frozen_N=len(rows),false_S_known=sum(r['GT']!='Supported' and r['predictions'].get(m)=='Supported' for r in rows)) for m in allmodels}
    result=dict(frozen_N=len(panel),new_HTTP200=sum(x['http_status']==200 for x in ledger),new_attempts=len(ledger),raw_common_N=len(raw),raw_common_patients=len({r['sid'] for r in raw}),score_common_N=len(core),invalid=dict(invalid),full_coverage=full_coverage,new_busy_price_or_reserved_cny=sum(x['cost_or_reserved_cny'] for x in ledger),unknown_reserved_cny=sum(x['cost_or_reserved_cny'] for x in ledger if x['http_status']==0),cost_by_arm=dict(costs),usage_by_arm=usage,raw_common_metrics=tables,score_common_metrics=secondary,raw_paired=comparisons,by_author=author,by_patient=patient,transitions=transitions)
    c.write_json(c.OUT/'a_analysis.json',result)
    print('A',dict(N=len(panel),raw_common=len(raw),score_common=len(core),cost=result['new_busy_price_or_reserved_cny'],correct={k:v['correct'] for k,v in tables.items()}))
if __name__=='__main__':main()
