"""Executor verification; no model calls, no changed labels, no independent audit claim."""
import ast,json,sys,subprocess
from collections import Counter
from decimal import Decimal
import numpy as np
from sklearn.metrics import accuracy_score,matthews_corrcoef,f1_score,confusion_matrix
import common093 as c
import api093
from operation093 import factor,encode_with_dictionary
from build_pool093 import render
def main():
    checks=[]
    def check(x,n):
        checks.append(dict(name=n,passed=bool(x)))
        if not x:raise AssertionError(n)
    jobs=api093.load_jobs();attempts,success,counts=api093.state()
    check(len(success)==len(jobs)==153,'all frozen logical requests complete exactly once')
    check(len({r['request_id'] for r in attempts if r['http_status']==200})==len(success),'one successful response per request')
    monetary=Decimal(0)
    for r in attempts:
        q=c.read(c.ROOT/r['request_path'])
        if r['http_status']==200:
            tr=c.read(c.ROOT/r['receipt_path'])['transport'];native=json.loads(tr['body_text']);u=native.get('usage',{})
            if type(u.get('prompt_tokens'))is int and type(u.get('completion_tokens'))is int:
                charge=(Decimal(u['prompt_tokens'])*3+Decimal(u['completion_tokens'])*9)/Decimal(1000000)
            else:charge=Decimal(str(q['reserved_cny']))
            check(native['model']=='deepseek-v4-flash-0731','returned model fixed')
        else:charge=Decimal(str(q['reserved_cny']))
        monetary+=charge;check(abs(float(charge)-r['cost_or_reserved_cny'])<1e-9,'independent charge')
    check(monetary<=20,'whole-task original-price cap')
    check(abs(float(monetary)-c.read(c.OUT/'cost_ledger.json')['original_or_reserved_cny'])<1e-8,'ledger total')
    for p,h in c.read(c.OUT/'source_manifest.json')['historical_sha256'].items():check(c.sha(c.ROOT/p)==h,'historical source unchanged '+p)
    check(c.sha(c.OUT/'engineering_archive/operation_inventory_v1.py')==c.read(c.OUT/'inventory_freeze.json')['operation_sha256'],'inventory initial source preserved')
    pool={r['id']:r for r in c.lines(c.PRIVATE/'pool_inputs.jsonl')};ops={r['id']:r for r in c.lines(c.OUT/'pool_operations.jsonl')}
    corpus={r['passage_id']:r for r in c.lines(c.ROOT/'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl')}
    for pid,row in pool.items():
        f=factor(row['B']);check(row['F']==f['reference'],'factoring deterministic '+pid)
        prefix=row['B'].split('1. Date:',1)[0];raw=render(prefix,ops[pid]['baseline_ids']+ops[pid]['added_ids'],corpus)
        packed,body=encode_with_dictionary(raw,f['dictionary']);check(packed==row['A'],'addition rendering '+pid)
        for key,value in f['dictionary'].items():body=body.replace(key,value)
        check(body==raw,'full reversible source expansion '+pid)
        check(len(row['A'])<=len(row['B']) and len(row['F'])<=len(row['B']),'fixed exact character budget '+pid)
        check(set(ops[pid]['baseline_ids'])<=set(r['passage_id'] for r in ops[pid]['source_records']),'no base source removed '+pid)
    rows=c.lines(c.OUT/'predictions_public.jsonl');check(len(rows)==len({r['id'] for r in rows})==120,'same full sample IDs')
    labels=['Supported','Not Supported','Not Addressed'];analysis=c.read(c.OUT/'analysis.json')
    for panel,d in analysis['panels'].items():
        full=[r for r in rows if r['panel']==panel];core=[r for r in full if all(r['arms'][a]['valid'] for a in ['B','F','A'])]
        raw=[r for r in full if all(r['arms'][a]['raw_valid'] for a in ['B','F','A'])]
        for method in ['raw','U0','U2','PriorG']:
            if not core:continue
            for arm,z in d['common_core_metrics'][method].items():
                y=[r['GT'] for r in core];pred=[r['Original'] if arm=='Original' else r['labels'][arm][method] for r in core]
                check(confusion_matrix(y,pred,labels=labels).tolist()==z['confusion_matrix'],'independent CM '+panel+method+arm)
                check(abs(accuracy_score(y,pred)-z['PA'])<1e-12,'independent PA')
                check(abs(matthews_corrcoef(y,pred)-z['MCC'])<1e-12,'independent MCC')
                check(abs(f1_score(y,pred,labels=labels,average='macro',zero_division=0)-z['Macro_F1'])<1e-12,'independent MacroF1')
        for method in ['raw','PriorG']:
            for comparison,z in d['comparisons'][method].items():
                if not z:continue
                new,base=comparison.split('-');rr=raw if method=='raw' else core
                rescue=sum(r['labels'][base][method]!=r['GT'] and r['labels'][new][method]==r['GT'] for r in rr)
                harm=sum(r['labels'][base][method]==r['GT'] and r['labels'][new][method]!=r['GT'] for r in rr)
                check((rescue,harm,rescue-harm)==(z['rescue'],z['harm'],z['net']),'rescue/harm conservation')
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));check(True,'syntax '+p.name)
    for p in c.OUT.rglob('*.jsonl'):
        for row in c.lines(p):check(not set(row)&{'text','claim','reference','body_text','reason','reasoning_content','api_key'},'no private raw fields '+p.name)
    check(subprocess.run(['git','check-ignore','-q','.local_models/093/main_jobs.jsonl'],cwd=c.ROOT).returncode==0,'private input ignored')
    paths=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines()
    check('.gitignore' not in paths,'gitignore unchanged')
    check(not any((p.startswith('outputs/') or p.startswith('tasks/')) and '/093_lossless_evidence_budget/' not in p for p in paths),'historical research not modified')
    c.put(c.OUT/'selfcheck.json',dict(status='PASS',checks=len(checks),failed=0,executor_selfcheck=True,independent_audit=False,original_price_or_reserved_cny=str(monetary),API_calls=len(attempts),utc=c.now()))
    print('Executor selfcheck PASS',len(checks),'cost',monetary)
if __name__=='__main__':main()
