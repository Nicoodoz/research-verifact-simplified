"""One evaluation path, paired patients, explanation bounds and real usage accounting."""
import json
from collections import Counter,defaultdict
import numpy as np
import common044 as c
import api044 as api
from stages044 import load_scores,audits
OUT=c.OUT/'results'

def summarize_scores(stage,cases,out):
    rows,term,attempts=load_scores(stage); truth={x['id']:x for x in cases}
    for r in rows: r['GT']=truth[r['id']]['GT']
    names=('base','rank','learned') if stage=='eval_score' else ('base','rank','complement','time')
    by={(r['id'],r['condition']):r for r in rows if r['round']==0}
    ids=sorted(x['id'] for x in cases if all(by[(x['id'],n)]['Score'] is not None for n in names))
    missing=[{'id':x['id'],'condition':n,'status':by[(x['id'],n)]['status']} for x in cases for n in names if by[(x['id'],n)]['Score'] is None]
    c.put(out/'coverage.json',dict(planned_n=len(cases),common_valid_n=len(ids),common_ids=ids,missing=missing,
      valid_by_condition={n:sum(by[(x['id'],n)]['Score'] is not None for x in cases) for n in names}))
    c.jsonl(out/'predictions.jsonl',rows)
    tables=[]; detail={}; patients=[]
    for scope in ('all','human','llm'):
        chosen=[i for i in ids if scope=='all' or truth[i]['author']==scope]
        if not chosen: continue
        cohort=[dict(proposition_id=i,subject_id=truth[i]['sid'],human_gt=truth[i]['GT']) for i in chosen]
        for name in names:
            for label in ('Score','U0','U2'):
                pr=[dict(proposition_id=i,verdict=by[(i,name)][label]) for i in chosen]
                metric=c.evaluate(cohort,pr,profile='research_patient',iterations=1000)
                key=f'{scope}/{name}/{label}'; detail[key]=metric
                row=dict(scope=scope,condition=name,label=label,n=len(chosen),
                  correct=sum(by[(i,name)][label]==truth[i]['GT'] for i in chosen),
                  PA=metric['percent_agreement'],MCC=metric['mcc'],AC1=metric['gwet_ac1'],
                  false_S=metric['per_class']['Supported']['fp'],
                  final_vs_Score_disagreement=sum(by[(i,name)][label]!=by[(i,name)]['Score'] for i in chosen))
                for lab,short in zip(c.LABELS,('S','NS','NA')):
                    for f in ('recall','precision','f1'): row[f'{short}_{f}']=metric['per_class'][lab][f]
                tables.append(row)
    for sid in sorted({truth[i]['sid'] for i in ids}):
        group=[i for i in ids if truth[i]['sid']==sid]
        cohort=[dict(proposition_id=i,subject_id=sid,human_gt=truth[i]['GT']) for i in group]
        for name in names:
            for label in ('Score','U0','U2'):
                pred=[dict(proposition_id=i,verdict=by[(i,name)][label]) for i in group]
                m=c.evaluate(cohort,pred,profile='none')
                patients.append(dict(sid=sid,condition=name,label=label,n=len(group),PA=m['percent_agreement'],
                  MCC=m['mcc'],correct=sum(by[(i,name)][label]==truth[i]['GT'] for i in group),false_S=m['per_class']['Supported']['fp']))
    c.csvwrite(out/'metrics.csv',tables); c.put(out/'metrics_full.json',detail); c.csvwrite(out/'patients.csv',patients)
    pairrows=[]; pairdetail={}; coh=[dict(proposition_id=i,subject_id=truth[i]['sid'],human_gt=truth[i]['GT']) for i in ids]
    comparisons=[('base',n) for n in names if n!='base']
    if 'learned' in names: comparisons.append(('rank','learned'))
    for a,b in comparisons:
        for lab in ('Score','U0','U2'):
            pa=[dict(proposition_id=i,verdict=by[(i,a)][lab]) for i in ids]
            pb=[dict(proposition_id=i,verdict=by[(i,b)][lab]) for i in ids]
            result=c.paired_compare(coh,pa,pb,iterations=1000); pairdetail[f'{b}-{a}/{lab}']=result
            fixes=sum(by[(i,a)][lab]!=truth[i]['GT'] and by[(i,b)][lab]==truth[i]['GT'] for i in ids)
            harms=sum(by[(i,a)][lab]==truth[i]['GT'] and by[(i,b)][lab]!=truth[i]['GT'] for i in ids)
            directions=[]; sid_delta={}
            for sid in sorted({truth[i]['sid'] for i in ids}):
                delta=sum(int(by[(i,b)][lab]==truth[i]['GT'])-int(by[(i,a)][lab]==truth[i]['GT']) for i in ids if truth[i]['sid']==sid)
                directions.append(delta); sid_delta[sid]=delta
            row=dict(baseline=a,candidate=b,label=lab,n=len(ids),rescued=fixes,harmed=harms,net_correct=fixes-harms,
              patient_positive=sum(v>0 for v in directions),patient_negative=sum(v<0 for v in directions),patient_tie=sum(v==0 for v in directions))
            for metric,short in [('percent_agreement','PA'),('mcc','MCC'),('gwet_ac1','AC1')]:
                r=result['metrics'][metric]; row[short+'_delta']=r['delta']; row[short+'_lo'],row[short+'_hi']=r['ci95']
            row['false_S_delta']=sum((by[(i,b)][lab]=='Supported')-(by[(i,a)][lab]=='Supported') for i in ids if truth[i]['GT']!='Supported')
            pairrows.append(row)
    c.csvwrite(out/'paired.csv',pairrows); c.put(out/'paired_full.json',pairdetail)
    repeats=[]; repids={r['id'] for r in rows if r['round']==1}
    lookup={(r['id'],r['condition'],r['round']):r for r in rows}
    for name in names:
        valid=[i for i in repids if lookup[(i,name,0)]['Score'] and lookup[(i,name,1)]['Score']]
        for lab in ('Score','U0','U2'):
            repeats.append(dict(condition=name,label=lab,n=len(valid),changed=sum(lookup[(i,name,0)][lab]!=lookup[(i,name,1)][lab] for i in valid),
              round0_correct=sum(lookup[(i,name,0)][lab]==truth[i]['GT'] for i in valid),
              round1_correct=sum(lookup[(i,name,1)][lab]==truth[i]['GT'] for i in valid)))
    c.csvwrite(out/'repeats.csv',repeats)
    return rows,by,ids,term,attempts,tables,pairrows

def summarize_reasons(cases,by,term):
    scope=c.read(c.OUT/'eval_audit/scope.json'); ids=set(scope['cohort_ids'])
    audit=audits('eval_audit',term); rows=[]; tables=[]
    for x in cases:
        if x['id'] not in ids: continue
        for name in ('base','rank','learned'):
            r=by[(x['id'],name)]; a=audit.get(r['request_id'],{})
            for lab in ('Score','U0','U2'):
                final=r.get(lab); valid=bool(final and a.get('status')=='valid')
                aligned=bool(valid and a.get('reason_label')==final)
                supported=c.joint_ok(a,final); correct=bool(final and final==x['GT'])
                rows.append(dict(id=x['id'],sid=x['sid'],author=x['author'],condition=name,label=lab,GT=x['GT'],final=final,
                  audit_valid=valid,reason_label=a.get('reason_label'),evidence_label=a.get('evidence_label'),
                  aligned=aligned,justification_pass=supported,joint_pass=correct and supported,unknown=not valid,
                  grounding=a.get('grounding'),coverage=a.get('coverage'),citation_valid=a.get('citation_valid'),note=a.get('note')))
    c.csvwrite(OUT/'explanation_cases.csv',rows)
    for name in ('base','rank','learned'):
        for lab in ('Score','U0','U2'):
            rr=[r for r in rows if r['condition']==name and r['label']==lab]; n=len(rr)
            passed=sum(r['joint_pass'] for r in rr); unknown=sum(r['unknown'] for r in rr)
            tables.append(dict(condition=name,label=lab,n=n,mode=scope['mode'],audit_valid=n-unknown,
              aligned=sum(r['aligned'] for r in rr),justification_pass=sum(r['justification_pass'] for r in rr),
              joint_pass=passed,joint_lower=passed/n,joint_upper=(passed+unknown)/n,missing_or_invalid=unknown))
    c.csvwrite(OUT/'explanation_summary.csv',tables)
    pairs=[]; lookup={(r['id'],r['condition'],r['label']):r for r in rows}
    sid={x['id']:x['sid'] for x in cases}; pats=sorted({sid[i] for i in ids})
    for a,b in [('base','rank'),('base','learned'),('rank','learned')]:
        for lab in ('Score','U0','U2'):
            aggregates=[]
            for p in pats:
                pp=[i for i in ids if sid[i]==p]
                delta=sum(int(lookup[(i,b,lab)]['joint_pass'])-int(lookup[(i,a,lab)]['joint_pass']) for i in pp)
                aggregates.append((len(pp),delta))
            ar=np.array(aggregates,float); draws=[]
            for seed in range(1000):
                selected=np.random.RandomState(seed).choice(len(pats),len(pats),replace=True)
                v=ar[selected].sum(axis=0); draws.append(v[1]/v[0])
            ci=np.percentile(draws,[2.5,97.5]).tolist()
            pairs.append(dict(baseline=a,candidate=b,label=lab,n=len(ids),joint_net=int(ar[:,1].sum()),
              joint_delta=float(ar[:,1].sum()/ar[:,0].sum()),ci_low=ci[0],ci_high=ci[1],
              estimand='paired patient lower-bound joint pass; unknown audit treated as not passed'))
    c.csvwrite(OUT/'explanation_paired.csv',pairs)
    return tables,pairs

def main():
    c.require(not OUT.exists(),'results exists'); OUT.mkdir(parents=True)
    cases=c.lines(c.OUT/'planning_001/eval_cases.jsonl')
    rows,by,ids,term,attempts,tables,pairs=summarize_scores('eval_score',cases,OUT)
    et,ep=summarize_reasons(cases,by,term)
    accounting=[]
    for a in attempts:
        t=term.get(a['request_id']); usage={}
        if t:
            try: usage=json.loads(t['transport']['body_text']).get('usage',{})
            except (ValueError,KeyError): pass
        accounting.append(dict(a,prompt_tokens=usage.get('prompt_tokens'),completion_tokens=usage.get('completion_tokens')))
    c.csvwrite(OUT/'cost_ledger.csv',accounting)
    cost=dict(total_attempts=len(attempts),terminal_HTTP200=len(term),estimate_cny=sum(a['charge_cny'] for a in attempts),
      cap_cny=c.CAP,basis='conservative catalog usage estimate, not reconciled bill',
      stages={stage:dict(attempts=sum(a['stage']==stage for a in attempts),cost=sum(a['charge_cny'] for a in attempts if a['stage']==stage))
        for stage in sorted({a['stage'] for a in attempts})},
      parser_status=dict(Counter(t['job']['kind']+'/'+t['parsed']['status'] for t in term.values())))
    c.put(OUT/'cost.json',cost)
    percondition=[]
    for name in ('base','rank','learned'):
        rr=[r for r in rows if r['condition']==name and r['round']==0]; vals=[]
        for r in rr:
            t=term[r['request_id']]; u=json.loads(t['transport']['body_text']).get('usage',{})
            if 'prompt_tokens' in u: vals.append((u['prompt_tokens'],u['completion_tokens'],c.charge(t['job'],t['transport'])[0]))
        ar=np.array(vals,float)
        percondition.append(dict(condition=name,n=len(vals),mean_input_tokens=float(ar[:,0].mean()),
          mean_output_tokens=float(ar[:,1].mean()),mean_single_call_cost=float(ar[:,2].mean()),online_Judge_calls=1))
    c.csvwrite(OUT/'deployment_cost.csv',percondition)
    summary=dict(planned_n=696,common_valid_n=len(ids),patients=len({x['sid'] for x in cases}),
      core_metrics=[r for r in tables if r['scope']=='all'],paired=pairs,explanation=et,explanation_paired=ep,
      model=c.read(c.OUT/'model/summary.json'),cost=cost,deployment_cost=percondition)
    c.put(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__': main()
