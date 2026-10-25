"""Execute the predeclared development-only 037 experiment, then stop."""
from __future__ import annotations
import argparse,json,shutil,subprocess
from pathlib import Path
import numpy as np
import core037 as c
import analyze037 as a

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    out=Path(args.output).resolve()
    assert out.parent==c.OUT.resolve(),'Output must be inside 037'
    out.mkdir(parents=True,exist_ok=False)
    datasets,folds,sources=c.old.load_data()
    views={k:datasets[k] for k in ('main40','old_R1')}
    dev=set(c.readj(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']['development'])
    assert len(views['main40'])==3675 and {r['sid'] for r in views['main40']}==dev
    assert all({r['sid'] for r in rs}<=dev for rs in views.values())
    source_paths=[c.ROOT/k for k in sources]+[c.ROOT/'tasks/022_competition_aware_support_calibration/calibration022.py',
        c.ROOT/'tasks/022_competition_aware_support_calibration/common022.py',c.ROOT/'tasks/035_lambda_boundary_calibration/common.py',
        c.ROOT/'src/verifact_research/evaluation/metrics.py']
    sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in source_paths}
    codes={p.name:c.sha(p) for p in c.TASK.iterdir() if p.suffix in ('.py','.md')}
    c.put(out/'freeze.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources=sources,codes=codes,datasets={k:c.describe(v) for k,v in views.items()},methods=list(c.METHODS),
        reserved_used=False,API_calls=0,evaluation_status='exploratory development following 036; not new confirmation',primary_pairs=c.PRIMARY_PAIRS))
    snapshot=out/'source';snapshot.mkdir()
    for name in codes:shutil.copyfile(c.TASK/name,snapshot/name)
    c.put(out/'inputs_numeric.json',views)
    fits=out/'fits';fits.mkdir()
    outputs={k:{m:np.full(len(rs),-1,int) for m in c.METHODS} for k,rs in views.items()}
    probs={k:{m:np.full((len(rs),3),np.nan) for m in c.METHODS} for k,rs in views.items()}
    aux={k:{s:np.full(len(rs),np.nan) for s in ('ratio','lr')} for k,rs in views.items()}
    learner=c.Learner();mainrows=views['main40']
    for f in range(4):
        train=[r for r in mainrows if r['fold']!=f];held=[r for r in mainrows if r['fold']==f]
        ins={s:np.full(len(train),-1 if s in ('v','m') else np.nan,int if s in ('v','m') else float) for s in ('v','m','ratio','lr')}
        inner=[]
        for h in sorted({r['fold'] for r in train}):
            tr=[r for r in train if r['fold']!=h]
            ii=[i for i,r in enumerate(train) if r['fold']==h];te=[train[i] for i in ii]
            model=learner.pipeline(tr);ss=c.infer(te,model)
            for k in ins:ins[k][ii]=ss[k]
            inner.append(dict(fold=int(h),split=c.split_meta(tr,te),pipeline=model))
        assert all(np.isfinite(x).all() for x in ins.values())
        _,ty=c.arrays(train)
        rt=c.select_threshold(ty,ins['v'],ins['m'],ins['ratio'],'ratio')
        lt=c.select_threshold(ty,ins['v'],ins['m'],ins['lr'],'lr')
        model=learner.pipeline(train)
        log=dict(fold=f,outer=c.split_meta(train,held),inner=inner,final_pipeline=model,ratio_selection=rt,lr_selection=lt,evaluation={})
        innerrows=[dict(id=r['id'],sid=r['sid'],fold=r['fold'],y=r['y'],
            **{k:int(ins[k][i]) if k in ('v','m') else float(ins[k][i]) for k in ins}) for i,r in enumerate(train)]
        c.writecsv(fits/f'fold{f}_inner_predictions.csv',innerrows)
        for name,rs in views.items():
            ii=np.array([i for i,r in enumerate(rs) if r['fold']==f]);te=[rs[i] for i in ii]
            if not len(ii):continue
            c.split_meta(train,te);ss=c.infer(te,model)
            pp,qq=c.make_outputs(te,ss,rt['selected']['threshold'],lt['selected']['threshold'])
            for method in c.METHODS:
                outputs[name][method][ii]=pp[method];probs[name][method][ii]=qq[method]
            for k in aux[name]:aux[name][k][ii]=ss[k]
            log['evaluation'][name]=c.describe(te)
        c.put(fits/f'fold{f}.json',log)
        print('Fit outer fold',f,'complete; no outer metrics inspected',flush=True)
    c.put(fits/'calibrator_training_ledger.json',learner.base_records)
    pred_dir=out/'frozen_predictions';pred_dir.mkdir()
    for name in views:
        assert all(np.all(p>=0) for p in outputs[name].values())
        assert all(np.isfinite(p).all() for p in probs[name].values())
        np.savez_compressed(pred_dir/f'{name}.npz',**{m+'_labels':p for m,p in outputs[name].items()},
            **{m+'_logprob':p for m,p in probs[name].items()},**aux[name])
    c.put(out/'prediction_freeze.json',dict(created_utc=c.now(),files={p.name:c.sha(p) for p in pred_dir.iterdir()}))
    anchor=c.ROOT/'outputs/036_final_validation/development_001/main40/frozen_predictions.npz'
    original=np.load(anchor);baseline_checks={}
    for m in ('U0','U2','Std_M','Std_V'):
        assert np.array_equal(outputs['main40'][m],original[m+'_labels']),'Baseline label mismatch: '+m
        diff=float(np.max(np.abs(probs['main40'][m]-original[m+'_logprob'])))
        assert diff<1e-10,'Baseline probabilities mismatch: '+m
        baseline_checks[m]=dict(exact_labels=True,max_logprob_difference=diff)
    c.put(out/'baseline_replay.json',dict(source=str(anchor.relative_to(c.ROOT)),sha256=c.sha(anchor),checks=baseline_checks))
    results={}
    for name,rs in views.items():
        results[name]=a.analyze(name,rs,outputs[name],probs[name],aux[name],out)
        print('Evaluated',name,flush=True)
    c.put(out/'analysis_summary.json',results)
    for path,h in sources.items():assert c.sha(c.ROOT/path)==h,'Protected input changed'
    c.put(out/'read_log.json',sorted(c.READS))
    c.put(out/'completion.json',dict(completed_utc=c.now(),status='executed_pending_verification',
        API_calls=0,reserved_used=False,calibrator_training_sets=len(learner.base_records)))
    c.put(out/'manifest.json',dict(files={p.relative_to(out).as_posix():c.sha(p) for p in out.rglob('*') if p.is_file()}))
    print('037 numerical execution complete',flush=True)

if __name__=='__main__':main()
