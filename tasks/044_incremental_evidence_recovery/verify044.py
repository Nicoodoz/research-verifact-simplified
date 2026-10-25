"""Offline executor replay, not an independent scientific audit."""
import json,os,socket
from collections import Counter
import numpy as np
import common044 as c
import api044 as api
from stages044 import fit_numeric,predict,choose,load_scores,audits
from selector044 import FEATURES,BUDGET

def main():
    def denied(*args,**kwargs): raise RuntimeError('044 verifier is offline')
    socket.create_connection=denied; socket.socket.connect=denied
    checks={}; freeze=c.read(c.OUT/'planning_001/freeze.json')
    for rel,h in freeze['sources'].items(): c.require(c.sha(c.ROOT/rel)==h,'input changed '+rel)
    for rel,h in freeze['code_at_freeze'].items(): c.require(c.sha(c.ROOT/rel)==h,'initial code changed '+rel)
    for rel,h in freeze['rerank_receipts'].items(): c.require(c.sha(c.ROOT/rel)==h,'source rerank changed')
    checks['frozen_inputs_and_receipts_unchanged']=True
    model_freeze=c.read(c.OUT/'model/freeze.json')
    for rel,h in model_freeze['source_code'].items(): c.require(c.sha(c.ROOT/rel)==h,'model freeze code changed '+rel)
    c.require(c.sha(c.OUT/'model/final.json')==model_freeze['model_sha'],'model hash')
    c.require(c.sha(c.OUT/'model/eval_choices.jsonl')==model_freeze['choices_sha'],'selection hash')
    c.require(c.sha(c.OUT/'eval_score/jobs.jsonl')==model_freeze['jobs_sha'],'eval jobs hash')
    train=c.lines(c.OUT/'planning_001/train_cases.jsonl'); test=c.lines(c.OUT/'planning_001/eval_cases.jsonl')
    c.require(len(train)==240 and len(test)==696,'cohorts')
    c.require({x['sid'] for x in train}.isdisjoint(x['sid'] for x in test),'patient overlap')
    checks['patient_separation']={'training_patients':len({x['sid'] for x in train}),'evaluation_patients':len({x['sid'] for x in test})}
    for x in train+test:
        for p in x['packs'].values():
            c.require(p['reference'].startswith(x['base']),'base was modified')
            c.require(len(p['reference'])-len(x['base'])==p['added_chars']<=BUDGET,'addition budget')
            c.require(len(p['ids'])<=2 and len(p['features'])==len(FEATURES),'pack/features')
            c.require(all(np.isfinite(p['features'])),'nonfinite features')
    checks['append_only_budget_and_features']=True
    data=c.lines(c.OUT/'model/training_pairs.jsonl'); model=c.read(c.OUT/'model/final.json')
    replay=fit_numeric(data)
    c.require(replay['classes']==model['classes'] and replay['kind']==model['kind'],'fit classes')
    if model['kind']=='logistic':
        for f in ('coef','intercept','mean','scale'): c.require(np.allclose(replay[f],model[f],rtol=1e-9,atol=1e-9),'fit replay '+f)
    choices={x['id']:x for x in c.lines(c.OUT/'model/eval_choices.jsonl')}
    for x in test:
        pred,values=choose(model,{'packs':x['packs']})
        c.require(pred==choices[x['id']]['choice'],'inference replay')
        c.require(all(abs(values[k]-choices[x['id']]['values'][k])<1e-10 for k in values),'utility replay')
    checks['model_refit_and_all_eval_choices_replayed']=True
    attempts,term=api.state(); used=sum(a['charge_cny'] for a in attempts)
    c.require(used<=c.CAP and len({a['request_id'] for a in attempts if a['http_status']==200})==len(term),'cost/success uniqueness')
    for stage in ('train_score','train_audit','eval_score','eval_audit'):
        f=c.read(c.OUT/stage/'freeze.json')
        c.require(c.sha(c.OUT/stage/'jobs.jsonl')==f['jobs_sha'],'jobs modified')
        c.require(c.sha(c.OUT/stage/'mapping.jsonl')==f['mapping_sha'],'mapping modified')
        jobs=c.lines(c.OUT/stage/'jobs.jsonl'); c.require(all(j['request_id'] in term for j in jobs),'incomplete stage')
        for j in jobs:
            payload=json.loads(j['body']['messages'][1]['content'])
            expected={'proposition','reference'} if j['kind']=='score' else {'proposition','reference','rationale'}
            c.require(set(payload)==expected,'API payload whitelist')
            c.require(term[j['request_id']]['job']==j,'terminal job identity')
            if j['kind']=='audit': c.require(set(payload['rationale'])=={'reason','checks'},'label hidden from auditor')
    checks['API_coverage_and_label_blinding']=dict(attempts=len(attempts),HTTP200=len(term),cost_cny=used,
      parser_status=dict(Counter(v['job']['kind']+'/'+v['parsed']['status'] for v in term.values())))
    rows,_,_=load_scores('eval_score'); by={(r['id'],r['condition']):r for r in rows if r['round']==0}
    ids=c.read(c.OUT/'results/coverage.json')['common_ids']; truth={x['id']:x for x in test}
    table=c.read(c.OUT/'results/summary.json')['core_metrics']
    for row in table:
        coh=[dict(proposition_id=i,subject_id=truth[i]['sid'],human_gt=truth[i]['GT']) for i in ids]
        pred=[dict(proposition_id=i,verdict=by[(i,row['condition'])][row['label']]) for i in ids]
        metric=c.evaluate(coh,pred,profile='none')
        c.require(abs(metric['percent_agreement']-row['PA'])<1e-12,'PA replay')
        c.require(abs(metric['mcc']-row['MCC'])<1e-12,'MCC replay')
        c.require(metric['per_class']['Supported']['fp']==row['false_S'],'falseS replay')
    checks['public_evaluation_replay']=True
    result=dict(status='pass',checked_utc=c.now(),independent_audit=False,checks=checks,
      known_scope='development-only; claim evidence audit is automatic, not clinical gold')
    serial=1+len(list(c.OUT.glob('verification_*.json')))
    c.put(c.OUT/f'verification_{serial:03}.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__': main()
