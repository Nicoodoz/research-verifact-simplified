"""Describe frozen recipe transfer and tradeoffs; no new fits or target selection."""
import sys
from collections import Counter
import numpy as np
import common080 as c
from fit080_v2 import predict,stats
sys.path.insert(0,str(c.ROOT/'tasks/078_component_ablation'))
import analyze078 as a

def main():
    models=c.read(c.OUT/'models_frozen.json');tr=c.lines(c.OUT/'calibration.jsonl');ev=c.lines(c.OUT/'predictions.jsonl')
    ref=models['full_models']['F4']['BASE']['reference_counts'];y=np.array([c.LABELS.index(x['GT']) for x in tr])
    base=predict(tr,'F4',models['full_models']['F4']['BASE']);out={}
    for recipe in ['WNLL1','WNLL2','WMCC1','WMCC2']:
        pred=predict(tr,'F4',models['full_models']['F4'][recipe]);changed=pred!=base
        trchanges=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],base=c.LABELS[b],candidate=c.LABELS[p],scores=x['F4']) for x,b,p in zip(tr,base,pred) if b!=p]
        evchanges=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],base=x['methods']['F4_BASE']['label'],candidate=x['methods']['F4_'+recipe]['label'],scores=x['arms']['F4']['scores']) for x in ev if x['methods']['F4_BASE']['label']!=x['methods']['F4_'+recipe]['label']]
        out[recipe]=dict(train_weighted_before=stats(y,base,ref),train_weighted_after=stats(y,pred,ref),
                        train_changes=trchanges,evaluation_changes=evchanges,train_changed_GT=dict(Counter(x['GT'] for x in trchanges)),
                        eval_changed_GT=dict(Counter(x['GT'] for x in evchanges)),
                        evaluation_pair_vs_old_F4=a.pair(ev,'F4_PriorG','F4_'+recipe))
    folds=c.read(c.OUT/'fold_models.json')
    counts={arm:{recipe:dict(Counter(c.canon(f['model']['delta']) for f in folds if f['model']['arm']==arm and f['model']['recipe']==recipe)) for recipe in ['WMCC1','WMCC2']} for arm in ['B','F4']}
    fallback=[dict(arm=f['model']['arm'],recipe=f['model']['recipe'],heldout=f['heldout_patient'],attempts=f['model']['details'].get('solver_attempts')) for f in folds if len(f['model']['details'].get('solver_attempts',[]))>1]
    c.put(c.OUT/'transfer_diagnosis.json',dict(type='post-analysis frozen-candidate comparisons; no parameter changes',recipes=out,fold_grid_parameters=counts,solver_fallbacks=fallback))
    print(c.canon(dict(recipes={r:{k:d[k] for k in ['train_changed_GT','eval_changed_GT']} for r,d in out.items()},fold_grid_parameters=counts,solver_fallbacks=len(fallback))))

if __name__=='__main__':main()
