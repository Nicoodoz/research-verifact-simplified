"""Stage transitions: pairwise supervision, local learning, frozen evaluation, blind audit."""
import json,math
from collections import Counter,defaultdict
import numpy as np
import common044 as c
import api044 as api
import selector044 as selector
from prepare044 import write_jobs,balanced

def load_scores(stage):
    attempts,term=api.state(); jobs=c.lines(c.OUT/stage/'jobs.jsonl')
    c.require(all(j['request_id'] in term for j in jobs),'stage not terminal')
    rows=[]
    for m in c.lines(c.OUT/stage/'mapping.jsonl'):
        p=term[m['request_id']]['parsed']; row=dict(m,status=p['status'])
        if p['status'] in c.VALID:
            row.update(Score=p['verdict'],U0=c.ulabel(p['scores'],0),U2=c.ulabel(p['scores'],2),
              scores=p['scores'],reason=(p.get('parsed') or {}).get('reason'))
        else: row.update(Score=None,U0=None,U2=None,scores=None,reason=None)
        rows.append(row)
    return rows,term,attempts

def build_train_audit():
    rows,term,_=load_scores('train_score'); rr={(x['id'],x['condition']):x for x in rows if x['round']==0}
    cases=c.lines(c.OUT/'planning_001/train_cases.jsonl'); chosen=set(); reasons={}
    for x in cases:
        base=rr[(x['id'],'base')]
        for name in ('rank','complement','time'):
            v=rr[(x['id'],name)]
            if base['Score'] and v['Score'] and v['Score']==x['GT'] and base['Score']!=x['GT']:
                chosen.add(v['request_id']); reasons[v['request_id']]='positive_utility'
    controls=sorted({v['request_id'] for v in rows if v['round']==0 and v['Score']},key=lambda r:c.hashrank('044/audit-control:',r))[:48]
    chosen.update(controls); specs=[]
    for rid in sorted(chosen):
        t=term[rid]; specs.append({'id':rid,'score_request_id':rid,'kind':'audit','model_key':'qwen',
          'selection_reason':reasons.get(rid,'fixed_hash_control'),'body':c.audit_body(t['job'],t['parsed'])})
    write_jobs('train_audit',specs)
    print('TRAIN AUDIT JOBS',len(specs),flush=True)

def audits(stage,term):
    return {m['score_request_id']:term[m['request_id']]['parsed'] for m in c.lines(c.OUT/stage/'mapping.jsonl')}

def fit_numeric(data):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    if not data or len({d['target'] for d in data})<2:
        label=data[0]['target'] if data else 0
        return dict(kind='constant',classes=[label],probabilities=[1.0],features=selector.FEATURES)
    X=np.array([d['features'] for d in data],float); y=np.array([d['target'] for d in data])
    weights=np.array([d['weight'] for d in data],float); weights/=weights.mean()
    scaler=StandardScaler().fit(X); X=scaler.transform(X)
    model=LogisticRegression(C=1,max_iter=2000,solver='lbfgs',random_state=44).fit(X,y,sample_weight=weights)
    return dict(kind='logistic',classes=model.classes_.tolist(),coef=model.coef_.tolist(),intercept=model.intercept_.tolist(),
      mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),features=selector.FEATURES,iterations=model.n_iter_.tolist())

def predict(model,features):
    if model['kind']=='constant': return float(sum(a*b for a,b in zip(model['classes'],model['probabilities'])))
    x=(np.array(features)-np.array(model['mean']))/np.array(model['scale'])
    z=np.array(model['coef'])@x+np.array(model['intercept'])
    if len(model['classes'])==2: z=np.r_[0.,z[0]]
    exp=np.exp(z-z.max()); probs=exp/exp.sum()
    return float(probs@np.array(model['classes']))

def choose(model,x):
    values={k:predict(model,p['features']) for k,p in x['packs'].items() if p['ids']}
    if not values: return 'base',{}
    order={'rank':0,'complement':1,'time':2}
    best=min(values,key=lambda k:(-values[k],order[k]))
    return (best if values[best]>.02 else 'base'),values

def fit_and_freeze():
    rows,term,_=load_scores('train_score'); audit=audits('train_audit',term)
    cases=c.lines(c.OUT/'planning_001/train_cases.jsonl')
    rr={(x['id'],x['condition']):x for x in rows if x['round']==0}; data=[]; exclusions=[]
    for x in cases:
        base=rr[(x['id'],'base')]; uniq={}
        for name,p in x['packs'].items():
            if p['ids']: uniq.setdefault(c.digest(p['reference']),(name,p))
        for name,p in uniq.values():
            v=rr[(x['id'],name)]
            if not base['Score'] or not v['Score']:
                exclusions.append({'id':x['id'],'condition':name,'reason':'invalid_score'}); continue
            delta=int(v['Score']==x['GT'])-int(base['Score']==x['GT']); target=delta
            if delta==1:
                a=audit.get(v['request_id'])
                if not a or a.get('status')!='valid':
                    exclusions.append({'id':x['id'],'condition':name,'reason':'invalid_positive_audit'}); continue
                if not c.joint_ok(a,v['Score']): target=0
            data.append(dict(id=x['id'],sid=x['sid'],condition=name,features=p['features'],raw_delta=delta,
              target=target,GT=x['GT'],weight=x['sampling_weight']/max(1,len(uniq))))
    c.jsonl(c.OUT/'model/training_pairs.jsonl',data); c.put(c.OUT/'model/training_exclusions.json',exclusions)
    foldmodels={}; oof=[]
    for sid in sorted({x['sid'] for x in cases}):
        model=fit_numeric([d for d in data if d['sid']!=sid]); foldmodels[sid]=model
        for x in cases:
            if x['sid']!=sid: continue
            choice,values=choose(model,{'packs':x['packs']})
            base=rr[(x['id'],'base')]; selected=rr[(x['id'],choice)]
            oof.append(dict(id=x['id'],sid=sid,GT=x['GT'],choice=choice,values=values,
              base=base['Score'],selected=selected['Score'],base_U2=base['U2'],selected_U2=selected['U2']))
    final=fit_numeric(data)
    c.put(c.OUT/'model/folds.json',foldmodels); c.jsonl(c.OUT/'model/oof.jsonl',oof)
    c.put(c.OUT/'model/final.json',final)
    summary=dict(created_utc=c.now(),training_pairs=len(data),raw_utility=dict(Counter(d['raw_delta'] for d in data)),
      qualified_utility=dict(Counter(d['target'] for d in data)),oof_choices=dict(Counter(d['choice'] for d in oof)),
      oof_correct_delta=sum(int(x['selected']==x['GT'])-int(x['base']==x['GT']) for x in oof if x['base'] and x['selected']),
      oof_U2_delta=sum(int(x['selected_U2']==x['GT'])-int(x['base_U2']==x['GT']) for x in oof if x['base_U2'] and x['selected_U2']),
      final_kind=final['kind'],threshold=.02,model_sha=c.sha(c.OUT/'model/final.json'))
    c.put(c.OUT/'model/summary.json',summary)
    build_eval(final)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

def build_eval(model):
    cases=c.lines(c.OUT/'planning_001/eval_cases.jsonl')
    repeats=set(c.read(c.OUT/'planning_001/freeze.json')['eval_repeat_ids']); specs=[]; selections=[]
    for x in cases:
        choice,values=choose(model,{'packs':x['packs']})
        selected=x['base'] if choice=='base' else x['packs'][choice]['reference']
        refs={'base':x['base'],'rank':x['packs']['rank']['reference'],'learned':selected}
        selections.append({'id':x['id'],'sid':x['sid'],'choice':choice,'values':values,
          'rank_added_chars':x['packs']['rank']['added_chars'],'learned_added_chars':len(selected)-len(x['base'])})
        for name,ref in refs.items():
            for rnd in ([0,1] if x['id'] in repeats else [0]):
                specs.append({'id':x['id'],'sid':x['sid'],'author':x['author'],'condition':name,'round':rnd,
                  'body':c.score_body(x['claim'],ref)})
    c.jsonl(c.OUT/'model/eval_choices.jsonl',selections)
    write_jobs('eval_score',specs)
    c.put(c.OUT/'model/freeze.json',dict(created_utc=c.now(),model_sha=c.sha(c.OUT/'model/final.json'),
      choices_sha=c.sha(c.OUT/'model/eval_choices.jsonl'),jobs_sha=c.sha(c.OUT/'eval_score/jobs.jsonl'),
      source_code={str(p.relative_to(c.ROOT)):c.sha(p) for p in c.TASK.glob('*.py')},
      eval_outcomes_seen=False,trained_patients=sorted({d['sid'] for d in c.lines(c.OUT/'model/training_pairs.jsonl')})))
    print('EVAL FROZEN',len(cases),'claims','choice_counts',dict(Counter(x['choice'] for x in selections)),flush=True)

def build_eval_audit():
    rows,term,attempts=load_scores('eval_score'); cases=c.lines(c.OUT/'planning_001/eval_cases.jsonl')
    chosen_ids={x['id'] for x in cases}; mode='full'; used=sum(a['charge_cny'] for a in attempts)
    candidates={x['request_id'] for x in rows if x['round']==0 and x['Score']}
    estimated=sum((len(term[r]['job']['body']['messages'][1]['content'])/3+2200)*3/1e6+.004 for r in candidates)
    if used+estimated>78:
        chosen_ids={x['id'] for x in balanced(cases,240,'044/eval-audit-sample:')}; mode='sampled_240'
    candidates={x['request_id'] for x in rows if x['round']==0 and x['Score'] and x['id'] in chosen_ids}
    specs=[]
    for rid in sorted(candidates):
        t=term[rid]; specs.append({'id':rid,'score_request_id':rid,'kind':'audit','model_key':'qwen',
          'body':c.audit_body(t['job'],t['parsed'])})
    write_jobs('eval_audit',specs)
    c.put(c.OUT/'eval_audit/scope.json',dict(mode=mode,cohort_ids=sorted(chosen_ids),cohort_n=len(chosen_ids),
      all_planned_n=696,used_cny=used,estimated_audit_cny=estimated,unique_audits=len(specs)))
    print('EVAL AUDIT',mode,len(chosen_ids),'claims',len(specs),'unique_outputs',flush=True)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('stage',choices=['train_audit','fit','eval_audit']); args=ap.parse_args()
    if args.stage=='train_audit': build_train_audit()
    elif args.stage=='fit': fit_and_freeze()
    else: build_eval_audit()
