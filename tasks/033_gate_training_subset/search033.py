"""One predeclared add/drop/swap batch, then freeze subsets before confirmation labels."""
import numpy as np
import common033 as s
from models033 import Models

def run():
    out=s.OUT/'search_001';s.require(not out.exists(),'Search exists');rows=s.lines(s.PREP/'rows_selection_blind.jsonl');old=[r for r in rows if r['partition']=='original16'];ff=s.candidate_rows(old);pool=sorted({r['subject_id'] for r in ff});rank=s.read(s.OUT/'historical_001/ranking.json');influence=s.read(s.OUT/'association_001/influence.json');panel=s.Panel([r for r in rows if r['partition']=='expansion'],s.read(s.P31/'before_models/A.json'));bank=Models(rows);plan=[];histbest={};seeds=[]
    for method in ('A','D'):
        mr=sorted([r for r in rank if r['method']==method],key=s.sort_key);histbest[method]=mr[0]
        for k in (8,11,14):
            seed=next(r for r in mr if r['k']==k);seeds.append(seed);inside=seed['train_patients'];outside=[p for p in pool if p not in inside];effect=lambda p:(influence[method+'/'+p]['equal_k_mean_effect'],p);low=min(inside,key=effect);high=max(outside,key=effect);highin=max(inside,key=effect);lowout=min(outside,key=effect)
            variants={'drop_low':set(inside)-{low},'add_high':set(inside)|{high},'swap_low_high':(set(inside)-{low})|{high},'reverse_swap_control':(set(inside)-{highin})|{lowout}}
            for operation,patients in variants.items():plan.append(dict(seed_method=method,seed_model=seed['model_id'],operation=operation,train_patients=sorted(patients),set_id=s.digest(sorted(patients))[:20]))
    unique={r['set_id']:r['train_patients'] for r in plan};s.require(len(unique)<=24,'Directed plan >24');out.mkdir();s.put(out/'directed_plan.json',dict(created_utc=s.now(),plan=plan,unique_sets=unique,rule='single batch from historical common-panel ranking/inclusion; no adaptive second pass',API_calls=0));s.put(out/'historical_best.json',histbest);s.put(out/'seeds.json',seeds)
    # Freeze all neighbor identities before fitting or inspecting any neighbor performance.
    directed=[];predictions=[];new_before=bank.new
    for i,(setid,patients) in enumerate(sorted(unique.items())):
        stats=s.training_summary(patients,old,ff)
        for method in ('A','D'):
            model,mid=bank.get(method,patients);prob=s.fit_probability(model,panel.candidates);record=dict(model_id=mid,set_id=setid,method=method,threshold=model['threshold'],**stats,**panel.evaluate(prob,model['threshold']));directed.append(record);predictions.extend(dict(model_id=mid,proposition_id=r['proposition_id'],probability=float(p),keep=bool(p>=model['threshold'])) for r,p in zip(panel.candidates,prob))
        s.status('directed batch',completed=i+1,total=len(unique),new_final_models=bank.new-new_before)
    s.require(bank.new-new_before<=48,'Directed fits >48');best={}
    for method in ('A','D'):best[method]=sorted([histbest[method],*[r for r in seeds if r['method']==method],*[r for r in directed if r['method']==method]],key=s.sort_key)[0]
    s.csvwrite(out/'directed_ranking.csv',sorted(directed,key=lambda r:(r['method'],*s.sort_key(r))));s.jsonl(out/'directed_candidate_predictions.jsonl',predictions);s.put(out/'selection_freeze.json',dict(created_utc=s.now(),historical_best=histbest,selected=best,ranking_rule=s.read(s.PREP/'config.json')['rank'],all_search_patients=s.read(s.PREP/'split.json')['expansion12'],confirmation_labels_connected=False,no_more_search=True,plan_sha256=s.sha(out/'directed_plan.json'),code={p.name:s.sha(p) for p in s.TASK.glob('*.py')}));bank.save('search_001/model_usage.json');s.put(out/'manifest.json',dict(created_utc=s.now(),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()}));s.status('subset selection frozen',best={m:r['train_patients'] for m,r in best.items()},new_final_fits=bank.new)

if __name__=='__main__':run()
