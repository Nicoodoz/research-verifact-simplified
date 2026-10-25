"""Train-selected models are frozen before connecting confirmation labels."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='4'
import numpy as np
import common032 as c
import learning032 as l

def run():
    c.block_network();cfg=c.read(c.OUT/'preparation_001/config.json');rows,data=l.load_arrays()
    gt={r['proposition_id']:r['human_gt'] for r in c.lines(c.OUT/'preparation_001/training_labels.jsonl')}
    y=np.array([c.LABELS.index(gt[r['proposition_id']]) if r['proposition_id'] in gt else -1 for r in rows])
    train=np.flatnonzero(y>=0);test=np.flatnonzero(y<0);folds=c.read(c.OUT/'preparation_001/folds.json')
    c.require(len(train)==2527 and len(test)==1148,'Training/confirmation scope')
    train_rows=[dict(rows[i],human_gt=c.LABELS[y[i]]) for i in train]
    cvout=c.OUT/'training_001';cvout.mkdir(exist_ok=True)
    freeze=dict(created_utc=c.now(),config_hash=c.digest(cfg),input_sha256=c.sha(c.OUT/'preparation_001/inputs_blind.jsonl'),training_labels_sha256=c.sha(c.OUT/'preparation_001/training_labels.jsonl'),nli_manifest_sha256=c.sha(c.OUT/'nli_001/manifest.json'),code={p.name:c.sha(p) for p in c.TASK.glob('*.py')},confirmation_GT_connected=False)
    freeze_path=cvout/'freeze.json'
    if not freeze_path.exists():c.put(freeze_path,freeze)
    else:
        saved=c.read(freeze_path)
        for k in ['config_hash','input_sha256','training_labels_sha256','nli_manifest_sha256','code']:c.require(saved[k]==freeze[k],'Training freeze changed '+k)
    base_metric=c.metric(train_rows,[rows[i]['u2'] for i in train]);all_cv=[];selections={}
    for family in cfg['families']:
        options=[]
        for hidden in cfg['hidden_sizes']:
            sums=np.zeros((len(rows),3),dtype='float64');counts=np.zeros(len(rows),dtype=int)
            for fold in folds:
                tr=np.array([i for i in train if rows[i]['subject_id'] in fold['training_patients']]);va=np.array([i for i in train if rows[i]['subject_id'] in fold['validation_patients']])
                c.require(not {rows[i]['subject_id'] for i in tr}&{rows[i]['subject_id'] for i in va},'Patient leakage')
                for seed in cfg['training_seeds']:
                    path=cvout/'models'/family/f'h{hidden}_f{fold["fold"]}_s{seed}'
                    net,stats=l.fitted(data,tr,y,family,hidden,seed,cfg,path,rows);sums[va]+=l.predict(net,stats,data,va);counts[va]+=1
                    c.state('training',state='running',family=family,hidden=hidden,fold=fold['fold'],seed=seed)
                print('CV',family,'hidden',hidden,'fold',fold['fold'],'complete',flush=True)
            c.require(np.all(counts[train]==len(cfg['training_seeds'])) and np.all(counts[test]==0),'OOF coverage/leakage')
            delta=sums[train]/counts[train,None];np.savez_compressed(cvout/f'{family}_h{hidden}_oof.npz',ids=np.array([rows[i]['proposition_id'] for i in train]),delta=delta)
            for scale in cfg['correction_scales']:
                z=l.base_logits(data,train,family)+scale*delta;m=c.metric(train_rows,l.decode(z))
                options.append(dict(family=family,hidden=hidden,scale=scale,meets_PA_constraint=m['PA']>=base_metric['PA']-1e-12,metrics=m))
        feasible=[v for v in options if v['meets_PA_constraint']]
        key=lambda v:(v['metrics']['MCC'],v['metrics']['PA'],-v['metrics']['false_S'],-v['hidden'],-v['scale'])
        chosen=max(feasible or options,key=key);chosen['constraint_failed']=not bool(feasible);selections[family]=chosen;all_cv.extend(options)
        c.put(cvout/'cv_metrics.json',all_cv);c.put(cvout/'selections.json',selections)
        print('Training-only selection',family,'hidden',chosen['hidden'],'scale',chosen['scale'],flush=True)
    c.put(cvout/'selection_freeze.json',dict(created_utc=c.now(),selections_sha256=c.sha(cvout/'selections.json'),all_scores_sha256=c.sha(cvout/'cv_metrics.json'),confirmation_GT_connected=False))
    final=c.OUT/'inference_001';final.mkdir(exist_ok=True);outputs={};models=[]
    for family,selected in selections.items():
        ds=[]
        for seed in cfg['training_seeds']:
            path=final/'models'/f'{family}_s{seed}'
            net,stats=l.fitted(data,train,y,family,selected['hidden'],seed,cfg,path,rows);ds.append(l.predict(net,stats,data,test));models.append(str(path/'model.json'))
        z=l.base_logits(data,test,family)+selected['scale']*np.mean(ds,axis=0);outputs[family]=l.decode(z)
        np.savez_compressed(final/f'{family}_logits.npz',logits=z,ids=np.array([rows[i]['proposition_id'] for i in test]))
    outputs['attention_candidate_only']=np.array([outputs['attention'][j] if rows[i]['candidate'] else rows[i]['u2'] for j,i in enumerate(test)])
    outputs['U0']=np.array([rows[i]['u0'] for i in test]);outputs['U2']=np.array([rows[i]['u2'] for i in test])
    historic={r['proposition_id']:r for r in c.lines(c.ROOT/'outputs/031_training_expansion_confirmation/inference_001/confirmation_predictions_blind.jsonl')}
    outputs['SD_A']=np.array([historic[rows[i]['proposition_id']]['methods']['after_A']['prediction'] for i in test])
    predictions=[]
    for j,i in enumerate(test):
        r=rows[i];predictions.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],candidate=r['candidate'],predictions={name:int(p[j]) for name,p in outputs.items()}))
    c.jsonl(final/'predictions_blind.jsonl',predictions)
    c.put(final/'manifest.json',dict(created_utc=c.now(),confirmation_GT_connected=False,predictions_sha256=c.sha(final/'predictions_blind.jsonl'),selections_sha256=c.sha(cvout/'selections.json'),models={p:c.sha(p) for p in models},n=len(predictions),training_patients=sorted({rows[i]['subject_id'] for i in train}),confirmation_patients=sorted({rows[i]['subject_id'] for i in test})))
    c.state('predictions_frozen',state='ready',n=len(predictions));print('All confirmation predictions frozen, no confirmation labels read',flush=True)
if __name__=='__main__':run()
