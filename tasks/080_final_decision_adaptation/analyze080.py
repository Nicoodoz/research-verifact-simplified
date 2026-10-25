"""Evaluate frozen calibration-selected080 methods; no fit or model selection here."""
import sys,copy
from threadpoolctl import threadpool_limits
import common080 as c
from fit080 import predict,RECIPES
sys.path.insert(0,str(c.ROOT/'tasks/078_component_ablation'))
import analyze078 as a

BASES=['Original','NS_U2','GateA','NS_StdM','NS_StdV','TS_raw','TS_U2','TS_PriorG','TS_newPriorG','F4_raw','F4_U2','F4_PriorG','F4_newPriorG']
METHODS=BASES+[arm+'_'+r for arm in ['B','F4'] for r in RECIPES]+['B_selected080','F4_selected080']
MAIN=['Original','TS_PriorG','TS_newPriorG','B_selected080','F4_PriorG','F4_newPriorG','F4_selected080','F4_U2']
PAIRS=[('F4_PriorG','F4_selected080'),('TS_PriorG','F4_selected080'),('B_selected080','F4_selected080'),('Original','F4_selected080'),
       ('TS_PriorG','B_selected080'),('F4_newPriorG','F4_selected080')]

def metrics(rows,method):
    m=a.metrics(rows,method)
    e=a.evaluate(a.cohort(rows),a.prediction(rows,method),profile='none',missing='error')
    m['per_class']=e['per_class'];m['macro_F1']=sum(e['per_class'][k]['f1'] or 0 for k in c.LABELS)/3
    m['balanced_accuracy']=sum(e['per_class'][k]['recall'] or 0 for k in c.LABELS)/3
    return m

def main():
    frozen=c.read(c.OUT/'models_frozen.json');assert frozen['status']=='FROZEN_BEFORE_080_EVALUATION'
    assert frozen['training_code_sha256']==c.sha(c.TASK/'fit080.py')
    assert frozen['source_freeze_sha256']==c.sha(c.OUT/'freeze.json')
    for key in ['TS_newPriorG','F4_newPriorG']:a.NAMES[key]=('B' if key.startswith('TS') else 'F4')+'＋079适配PriorG'
    for arm in ['B','F4']:
        for recipe in RECIPES:a.NAMES[arm+'_'+recipe]=arm+'＋'+recipe
        a.NAMES[arm+'_selected080']=arm+'＋080选定（'+frozen['selection'][arm]['chosen']+'）'
    source=c.ROOT/'outputs/079_f4_priorg_adaptation/predictions.jsonl'
    rows=copy.deepcopy(c.lines(source));assert len(rows)==352
    training={x['sid'] for x in c.lines(c.OUT/'calibration.jsonl')};assert not training&{x['sid'] for x in rows}
    c.put(c.OUT/'evaluation_apply_freeze.json',dict(created_utc=c.now(),model_sha256=c.sha(c.OUT/'models_frozen.json'),analysis_sha256=c.sha(c.TASK/'analyze080.py'),
        prediction_source_sha256=c.sha(source),calibration_selected=frozen['selection'],target_GT_used_for_selection=False))
    for arm,scorearm in [('B','TS'),('F4','F4')]:
        good=[x for x in rows if x['arms'][scorearm]['valid']]
        inference=[dict(id=x['id'],**{arm:x['arms'][scorearm]['scores']}) for x in good]
        byrecipe={recipe:{x['id']:c.LABELS[p] for x,p in zip(good,predict(inference,arm,m))} for recipe,m in frozen['full_models'][arm].items()}
        for x in rows:
            for recipe in RECIPES:
                base=x['methods'][scorearm+'_raw'];label=byrecipe[recipe].get(x['id'],x['methods']['NS_U2']['label'])
                x['methods'][arm+'_'+recipe]=dict(label=label,valid=base['valid'],fallback=base['fallback'],judge_cost_cny=base['judge_cost_cny'],arm=scorearm)
            x['methods'][arm+'_selected080']=dict(x['methods'][arm+'_'+frozen['selection'][arm]['chosen']])
    old128={x['id'] for x in c.lines(c.ROOT/'outputs/078_component_ablation/f4_blind.jsonl')}
    groups={'all352':rows,'common_core340':[x for x in rows if x['arms']['TS']['valid'] and x['arms']['F4']['valid']],
            'human':[x for x in rows if x['author']=='human'],'llm':[x for x in rows if x['author']=='llm'],'original_pool_isolated128':[x for x in rows if x['id'] in old128]}
    assert len(groups['common_core340'])==340 and len(groups['original_pool_isolated128'])==128
    tables={};pairs={};changes={}
    for name,rr in groups.items():
        tables[name]=[metrics(rr,m) for m in METHODS]
        pairs[name]=[a.pair(rr,b,f) for b,f in (PAIRS if name=='all352' else PAIRS[:3])]
        changes[name]=[{k:p[k] for k in ['base','candidate','rescue','harm','net','delta_falseS']}|{'label_changes':sum(x['methods'][p['base']]['label']!=x['methods'][p['candidate']]['label'] for x in rr)} for p in pairs[name]]
        print(c.canon(dict(cohort=name,n=len(rr),changes=changes[name])),flush=True)
    c.jl(c.OUT/'predictions.jsonl',rows);c.put(c.OUT/'tables.json',tables);c.put(c.OUT/'paired_comparisons.json',pairs);c.put(c.OUT/'changes.json',changes)
    old={x['method']:x for x in c.read(c.ROOT/'outputs/079_f4_priorg_adaptation/tables.json')['all352']}
    for m in tables['all352']:
        if m['method'] in old:
            for k in ['MCC','PA','AC1','correct','falseS','fallback']:assert m[k]==old[m['method']][k]
    c.put(c.OUT/'verification.json',dict(status='PASS',train_eval_patient_overlap=0,OOF_training_and_prior_exclude_heldout=True,
        old352_metrics_exact=True,parameter_models=frozen['fitted_parameter_models'],NLL_fits=frozen['NLL_optimizer_fits'],MCC_grid_fits=frozen['MCC_grid_selections'],
        new_API_calls=0,cost_cny=0,reserved_used=False,independent_audit='not performed',
        selected_recipes={arm:frozen['selection'][arm]['chosen'] for arm in ['B','F4']},evaluation_selected_winner=False))

if __name__=='__main__':
    with threadpool_limits(limits=1):main()
