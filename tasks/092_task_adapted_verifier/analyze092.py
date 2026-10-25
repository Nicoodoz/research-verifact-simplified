"""Join labels only after all ten fold/model predictions exist; fixed same-ID comparisons."""
from collections import Counter
import sys
import numpy as np
import common092 as c
from metrics092 import metrics
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare
def paired(rows,base,candidate,repeats=1000):
    y=np.array([c.LABELS.index(r['GT']) for r in rows]);a=np.array([c.LABELS.index(r['predictions'][base]) for r in rows]);b=np.array([c.LABELS.index(r['predictions'][candidate]) for r in rows]);sids=sorted({r['sid'] for r in rows});ix=[np.array([i for i,r in enumerate(rows) if r['sid']==s]) for s in sids]
    rescue=(a!=y)&(b==y);harm=(a==y)&(b!=y);patient={s:int((rescue[ii].astype(int)-harm[ii]).sum()) for s,ii in zip(sids,ix)};rng=np.random.RandomState(92092);diff=[]
    for _ in range(repeats):
        take=np.concatenate([ix[j] for j in rng.randint(0,len(ix),len(ix))]);ma=metrics(y[take],a[take]);mb=metrics(y[take],b[take]);diff.append([mb[k]-ma[k] for k in ['PA','MCC','Macro_F1']])
    official=paired_compare([dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows],[dict(proposition_id=r['id'],verdict=r['predictions'][base]) for r in rows],[dict(proposition_id=r['id'],verdict=r['predictions'][candidate]) for r in rows],iterations=repeats)
    return dict(base=base,candidate=candidate,N=len(rows),patients=len(sids),rescue=int(rescue.sum()),harm=int(harm.sum()),net=int(rescue.sum()-harm.sum()),rescue_by_GT={lab:int(rescue[y==j].sum()) for j,lab in enumerate(c.LABELS)},harm_by_GT={lab:int(harm[y==j].sum()) for j,lab in enumerate(c.LABELS)},false_S_added=int(((b==0)&(a!=0)&(y!=0)).sum()),false_S_prevented=int(((a==0)&(b!=0)&(y!=0)).sum()),patient_net=patient,patient_win_loss_tie=[sum(v>0 for v in patient.values()),sum(v<0 for v in patient.values()),sum(v==0 for v in patient.values())],official_paired_compare=official,independent_supplement_CI95={k:np.quantile(np.asarray(diff)[:,i],[.025,.975]).tolist() for i,k in enumerate(['PA','MCC','Macro_F1'])},bootstrap_note='Fixed OOF predictions; no retraining; exploratory interval does not cover model-selection or training randomness.')
def table(rows,models):
    y=[c.LABELS.index(r['GT']) for r in rows];result={}
    for m in models:
        z=metrics(y,[c.LABELS.index(r['predictions'][m]) for r in rows],[r['probabilities'][m] for r in rows] if m in ['frozen','finetuned'] else None)
        official=evaluate([dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows],[dict(proposition_id=r['id'],verdict=r['predictions'][m]) for r in rows],profile='none',missing='error')
        for key,oldkey in [('PA','percent_agreement'),('MCC','mcc'),('AC1','gwet_ac1')]:assert abs(z[key]-official[oldkey])<1e-10;z[key]=official[oldkey]
        assert z['confusion_matrix']==official['confusion_matrix'];z['official_evaluator_verified']=True;result[m]=z
    return result
def main():
    folds=c.read(c.OUT/'folds.json');base=c.lines(c.OUT/'cohort.jsonl');bags={r['id']:r for r in c.lines(c.OUT/'bags.jsonl')};pred={};cost=[]
    for family in ['frozen','finetuned']:
        pred[family]={}
        for f in folds:
            folder=c.OUT/f"{family}_fold{f['fold']}";done=c.read(folder/'complete.json');assert done['config_sha256']==c.sha(c.TASK/'config.json');cost.append(done)
            for r in c.lines(folder/'predictions.jsonl'):
                assert r['sid'] in f['test'] and r['sid'] not in f['train']+f['validation'];assert r['id'] not in pred[family];pred[family][r['id']]=r
        assert set(pred[family])=={r['id'] for r in base}
    baselines={(r['id'],r['arm']):r for r in c.lines(c.OUT/'cached_baselines.jsonl')};rows=[]
    for r in base:
        pid=r['id'];x=dict(r,fold=pred['frozen'][pid]['fold'],predictions={'Original':r['original']},probabilities={},reference_sha256=bags[pid]['reference_sha256'],C48_source=bags[pid]['source'],evidence_tokens=bags[pid]['evidence_tokens'],windows=len(bags[pid]['windows']))
        for m in ['frozen','finetuned']:x['predictions'][m]=pred[m][pid]['prediction'];x['probabilities'][m]=pred[m][pid]['probabilities']
        for m in ['B','F4']:
            if (pid,m) in baselines:x['predictions'][m]=baselines[pid,m]['label']
        rows.append(x)
    c.jsonl(c.OUT/'oof_predictions.jsonl',rows)
    models=['Original','frozen','finetuned'];main_table=table(rows,models);common=[r for r in rows if all(m in r['predictions'] for m in ['B','F4'])];all_models=['Original','B','F4','frozen','finetuned']
    summaries={'full_OOF':main_table,'cached_B_F4_common':table(common,all_models)}
    demos={str(e['sid']) for e in c.read(c.ROOT/'outputs/071_judge_icl_feasibility/freeze.json')['examples']}
    summaries['cached_common_excluding_actual_demo_patients']=table([r for r in common if r['sid'] not in demos],all_models)
    summaries['cached_common_core_valid']=table([r for r in common if all(baselines[r['id'],arm]['valid'] for arm in ['B','F4'])],all_models)
    c.put(c.OUT/'baseline_validity.json',{arm:dict(N=len(common),valid=sum(baselines[r['id'],arm]['valid'] for r in common),fallback=sum(baselines[r['id'],arm]['fallback'] for r in common)) for arm in ['B','F4']})
    subgroup={}
    for field in ['author','historical_role','C48_source','fold','time_metadata_conflict','initial_agreement']:
        subgroup[field]={str(v):table([r for r in rows if r[field]==v],models) for v in sorted({r[field] for r in rows})}
    subgroup['cached_sources']={source:table([r for r in common if baselines[r['id'],'B']['source']==source],all_models) for source in sorted({baselines[r['id'],'B']['source'] for r in common})}
    # Preserve the natural and pressure panels as separate comparable subsets.
    ninety=c.lines(c.ROOT/'outputs/090_demo_constructor_repair_validation/predictions_public.jsonl')
    for panel in ['natural','pressure']:
        source={r['id']:r for r in ninety if r['panel']==panel};rr=[]
        for r in rows:
            if r['id'] in source:
                x=dict(r,predictions=dict(r['predictions']));x['predictions'].update({m:source[r['id']]['labels'][m]['PriorG'] for m in ['B','F4']});rr.append(x)
        if rr:subgroup['090_'+panel]=table(rr,all_models)
    pairs={'finetuned_vs_frozen':paired(rows,'frozen','finetuned'),'finetuned_vs_author':paired(rows,'Original','finetuned'),'frozen_vs_author':paired(rows,'Original','frozen')}
    for m in ['B','F4']:pairs['common_finetuned_vs_'+m]=paired(common,m,'finetuned')
    patients={s:table([r for r in rows if r['sid']==s],models) for s in sorted({r['sid'] for r in rows})}
    representatives=[]
    for category in c.LABELS:
        for typ in ['rescue','harm']:
            candidates=[r for r in rows if r['GT']==category and ((r['predictions']['frozen']!=r['GT'] and r['predictions']['finetuned']==r['GT']) if typ=='rescue' else (r['predictions']['frozen']==r['GT'] and r['predictions']['finetuned']!=r['GT']))]
            if candidates:
                r=min(candidates,key=lambda r:c.digest('092-case-v1:'+r['id']));representatives.append(dict(type=typ,**r))
    transitions={}
    for baseline,scope in [('frozen',rows),('Original',rows),('B',common),('F4',common)]:
        cc=Counter((r['GT'],r['predictions'][baseline],r['predictions']['finetuned'],r['author']) for r in scope)
        transitions[baseline]=[dict(GT=k[0],baseline_prediction=k[1],finetuned_prediction=k[2],author=k[3],count=v) for k,v in sorted(cc.items())]
    c.put(c.OUT/'class_transitions.json',transitions)
    c.put(c.OUT/'metrics.json',summaries);c.put(c.OUT/'subgroups.json',subgroup);c.put(c.OUT/'paired.json',pairs);c.put(c.OUT/'patients.json',patients);c.jsonl(c.OUT/'representative_cases.jsonl',representatives);c.put(c.OUT/'costs.json',dict(API_calls=0,API_cost_cny=0,API_cap_cny=30,local_rental_cny=None,electricity_cost_unknown=True,training=cost,c48=c.read(c.OUT/'c48_manifest.json'),encoding=c.read(c.OUT/'cache_manifest.json')))
    out=['# 092结果表','数值来自完整OOF；B/F4共同集合是历史混合选样，不代表自然分布。','']
    for name,tt in summaries.items():
        out+=['## '+name,'','|配置|MCC|PA|正确/N|错误支持/non-S|S假发现率|Macro-F1|','|---|---:|---:|---:|---:|---:|---:|']
        for m,z in tt.items():out.append(f"|{m}|{z['MCC']:.4f}|{z['PA']:.2%}|{z['correct']}/{z['N']}|{z['false_S']}/{z['true_non_S']}|{z['false_discovery_S']:.2%}|{z['Macro_F1']:.4f}|")
        out+=['']
    (c.OUT/'tables.md').write_text('\n'.join(out)+'\n',encoding='utf-8');print(summaries,flush=True)
if __name__=='__main__':main()
