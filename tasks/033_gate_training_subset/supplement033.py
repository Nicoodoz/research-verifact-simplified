"""Descriptive closeout tables: ties, enrichment, one-step changes and patient directions."""
from collections import Counter,defaultdict
import numpy as np
import common033 as s

def main():
    out=s.OUT/'supplement_001';s.require(not out.exists(),'Supplement exists');rank=s.read(s.OUT/'historical_001/ranking.json');freeze=s.read(s.OUT/'search_001/selection_freeze.json');ids=s.read(s.OUT/'historical_001/model_ids.json');probs=np.load(s.OUT/'historical_001/search_probability.npy');index={p:i for i,p in enumerate(ids)};stats=[];enrichment=[];ties={};pool=sorted({p for r in rank for p in r['train_patients']})
    for method in ('A','B','D'):
        rr=[r for r in rank if r['method']==method]
        for k in (3,5,8,11,14):
            part=[r for r in rr if r['k']==k];good=[r for r in part if r['eligible_retention80']];chosen=sorted(part,key=s.sort_key)[0];stats.append(dict(method=method,k=k,sets=len(part),eligible80=len(good),best_model=chosen['model_id'],best_patients=chosen['train_patients'],best_R=chosen['R'],best_risk=chosen['risk'],best_MCC=chosen['MCC'],best_correct=chosen['correct'],best_retention=chosen['rescue_retention'],best_robust_gain=chosen['robust_gain_per100R'],**{f+'_mean':np.mean([r[f] for r in part]) for f in ('rescue_retention','risk','robust_gain_per100R','MCC','correct')}))
            ref=good if good else part;cut=np.percentile([r['robust_gain_per100R'] for r in ref],90);top=[r for r in ref if r['robust_gain_per100R']>=cut-1e-10]
            for p in pool:enrichment.append(dict(method=method,k=k,patient=p,all_sets=len(part),top_sets=len(top),top_ties_retained=True,n_top_in=sum(p in r['train_patients'] for r in top),n_all_in=sum(p in r['train_patients'] for r in part),top_fraction=sum(p in r['train_patients'] for r in top)/len(top),all_fraction=sum(p in r['train_patients'] for r in part)/len(part)))
        if method in freeze['selected']:
            b=freeze['selected'][method];target=probs[index[b['model_id']]]>=b['threshold'];same=[r for r in rr if np.array_equal(probs[index[r['model_id']]]>=r['threshold'],target)];ties[method]=dict(selected_model=b['model_id'],same_search_workpoint_n=len(same),by_k=dict(Counter(r['k'] for r in same)),model_ids=[r['model_id'] for r in same],note='Identical91 candidate actions on the search panel, not globally equivalent coefficients or out-of-patient behavior')
    directed=s.csvread(s.OUT/'search_001/directed_ranking.csv');dr={(r['set_id'],r['method']):r for r in directed};old={r['model_id']:r for r in rank};changes=[]
    for p in s.read(s.OUT/'search_001/directed_plan.json')['plan']:
        before=old[p['seed_model']];after=dr[p['set_id'],p['seed_method']];changes.append(dict(**p,**{f+'_delta':float(after[f])-before[f] for f in ('R','risk','rescue_retention','correct','MCC','robust_gain_per100R')}))
    evaluation=s.OUT/'evaluation_001';pm=s.csvread(evaluation/'patients.csv');directions=[];pair=s.read(evaluation/'paired.json')
    for key in pair:
        scope,comparison=key.split('/');new,base=comparison.split('-minus-');ix={(r['subject_id'],r['configuration']):r for r in pm if r['scope']==scope};ss=sorted({p for p,m in ix});d=[int(ix[p,new]['correct'])-int(ix[p,base]['correct']) for p in ss];directions.append(dict(scope=scope,comparison=comparison,positive=sum(x>0 for x in d),negative=sum(x<0 for x in d),ties=sum(x==0 for x in d),deltas=dict(zip(ss,d))))
    held=s.csvread(s.OUT/'association_001/original_held_adjusted_inclusion.csv');heldsummary=[]
    for m in ('A','D'):
        for p in pool:
            for group in ('025','026'):
                rr=[r for r in held if r['method']==m and r['training_patient']==p and r['held_group']==group and r['adequate_cells']=='True'];vals=[float(r['correct_in_minus_out']) for r in rr];heldsummary.append(dict(method=m,patient=p,test_group=group,adequate_strata=len(rr),positive_strata=sum(x>0 for x in vals),negative_strata=sum(x<0 for x in vals),mean_correct_effect=np.mean(vals) if vals else None))
    allrows=s.lines(evaluation/'full_rows.jsonl');ff=s.candidate_rows(allrows);profiles=[]
    for p in sorted({r['subject_id'] for r in allrows}):
        cc=[r for r in ff if r['subject_id']==p];rr=[r for r in allrows if r['subject_id']==p];profiles.append(dict(subject_id=p,group=rr[0]['group'],partition=rr[0]['partition'],**s.training_summary([p],allrows,ff),**{'mean_'+k:np.mean([r['features'][k] for r in cc]) if cc else None for k in ('s','ns','na','s_margin','peer_s','repeat_s','fraction_supported')}))
    out.mkdir();s.csvwrite(out/'size_best_and_distribution.csv',stats);s.csvwrite(out/'top_decile_membership.csv',enrichment);s.put(out/'identical_search_actions.json',ties);s.csvwrite(out/'directed_changes.csv',changes);s.put(out/'patient_directions.json',directions);s.csvwrite(out/'patient_directions.csv',directions);s.csvwrite(out/'original_inclusion_group_summary.csv',heldsummary);s.csvwrite(out/'all40_patient_profiles.csv',profiles);s.put(out/'manifest.json',dict(created_utc=s.now(),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()},no_fits=True,no_new_selection=True));s.status('descriptive supplements complete')

if __name__=='__main__':main()
