"""Execute the frozen 035 numerical study; no network or existing-output overwrite."""
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np
import common as c
import learning as l
import analysis as a

def fitted_group(source_name,source,targets,out):
    outputs={name:{m:(np.full(len(rr),-1,dtype=int),np.full((len(rr),3),np.nan)) for m in c.METHODS} for name,rr in targets.items()}
    fitdir=out/'fits'/source_name;fitdir.mkdir(parents=True,exist_ok=False)
    for fold in range(4):
        train=[r for r in source if r['fold']!=fold];train_sids=set(r['sid'] for r in train)
        assert train and len({r['id'] for r in train})==len(train)
        models,states=l.fit_all(train)
        record=dict(source=source_name,fold=fold,training_patients=sorted(train_sids),training_ids=[r['id'] for r in train],
          training_label_sha256=hashlib.sha256(json.dumps([(r['id'],r['y']) for r in train]).encode()).hexdigest(),models=models,evaluation={})
        c.csvwrite(fitdir/f'fold{fold}_states.csv',states)
        for name,rr in targets.items():
            ii=np.array([i for i,r in enumerate(rr) if r['fold']==fold]);held=[rr[i] for i in ii]
            if not held:continue
            assert train_sids.isdisjoint(r['sid'] for r in held),'Patient overlap'
            pp=l.infer(held,models);record['evaluation'][name]=dict(patients=sorted(set(r['sid'] for r in held)),ids=[r['id'] for r in held])
            for m,(p,lp) in pp.items():outputs[name][m][0][ii]=p;outputs[name][m][1][ii]=lp
        c.put(fitdir/f'fold{fold}.json',record)
        print(source_name,'fold',fold,'lambda',models['Task_T']['lam'],models['Robust_T']['lam'],'T2',models['U2_T']['T'],flush=True)
    for name,pp in outputs.items():
        assert all(np.all(v[0]>=0) and np.isfinite(v[1]).all() for v in pp.values())
        assert np.array_equal(pp['U2'][0],pp['U2_T'][0])
    return outputs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    datasets,folds,sources=c.load_data()
    import scipy,matplotlib
    code={str(p.relative_to(c.ROOT)):c.sha(p) for p in c.TASK.glob('*') if p.is_file()}
    c.put(out/'freeze.json',dict(created_utc=c.now(),sources=sources,code=code,folds=folds,
      environment=dict(python=sys.version,executable=sys.executable,numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__),
      methods=list(c.METHODS),new_API_calls=0,reserved_used=False,protocol='../protocol.md'))
    c.put(out/'inputs_numeric.json',datasets)
    predictions={};target_rows={}
    jobs=[('old_R0',{'old_R0':datasets['old_R0'],'old_R1':datasets['old_R1']}),
      ('main40',{'main40':datasets['main40']}),
      ('bridge_deepseek',{'bridge_deepseek':datasets['bridge_deepseek'],'DS_to_Q':datasets['bridge_qwen']}),
      ('bridge_qwen',{'bridge_qwen':datasets['bridge_qwen'],'Q_to_DS':datasets['bridge_deepseek']})]
    for source,targets in jobs:
        predictions.update(fitted_group(source,datasets[source],targets,out));target_rows.update(targets)
    full,states=l.fit_all(datasets['main40']);c.put(out/'full_development_models.json',dict(models=full,training_ids=[r['id'] for r in datasets['main40']],not_generalization_results=True))
    blind=out/'frozen_predictions';blind.mkdir()
    for name,pp in predictions.items():
        np.savez_compressed(blind/(name+'.npz'),**{m+'_'+k:vals[j] for m,vals in pp.items() for j,k in enumerate(['labels','logprob'])})
    c.put(out/'prediction_freeze.json',dict(created_utc=c.now(),files={p.name:c.sha(p) for p in blind.iterdir()}))
    alltable=[]
    for name,pp in predictions.items():
        alltable.extend(a.analyze(name,target_rows[name],pp,out));print('Evaluated',name,flush=True)
    c.csvwrite(out/'all_metrics.csv',alltable)
    stability=[];lookup={r['id']:i for i,r in enumerate(target_rows['old_R0'])}
    ix=np.array([lookup[r['id']] for r in target_rows['old_R1']]);y=np.array([r['y'] for r in target_rows['old_R1']])
    for m in c.METHODS:
        p=predictions['old_R0'][m][0][ix];q=predictions['old_R1'][m][0]
        stability.append(dict(method=m,n=len(ix),label_flips=int(sum(p!=q)),correct_R0=int(sum(p==y)),correct_R1=int(sum(q==y))))
    c.csvwrite(out/'repeat_stability.csv',stability)
    transfer={}
    for source,target in [('DS_to_Q','bridge_qwen'),('Q_to_DS','bridge_deepseek')]:
        rr=target_rows[target]
        for m in ('U2_T','Joint_NLL','Task_T','Robust_T'):
            b=predictions[target][m];p=predictions[source][m]
            comparison=c.paired_compare(c.cohort(rr),c.predictions(rr,b[0]),c.predictions(rr,p[0]),iterations=1000)
            comparison['probability_and_risk']=a.paired_extra(rr,b,p)
            transfer[source+'/'+m]=comparison
    c.put(out/'transfer_vs_refit.json',transfer)
    for dataset,n,correct in [('main40',3675,3012),('old_R0',1529,1285),('old_R1',879,708)]:
        m=next(r for r in alltable if r['dataset']==dataset and r['scope']=='all' and r['method']=='U2')
        assert m['n']==n and m['correct']==correct,'Historical U2 anchor mismatch'
    for rel,value in sources.items():assert c.sha(c.ROOT/rel)==value,'Input changed'
    c.put(out/'completion.json',dict(completed_utc=c.now(),status='executed_pending_verification',datasets=list(predictions),new_API_calls=0))
    c.put(out/'manifest.json',{str(p.relative_to(out)):c.sha(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'})
    print('035 lambda boundary calibration complete',flush=True)

if __name__=='__main__':main()
