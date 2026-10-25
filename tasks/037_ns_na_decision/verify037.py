"""Executor scientific verification, not an independent audit."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
import core037 as c
import analyze037 as a


def verify_pipeline(meta, allowed, excluded, ledger):
    tr=set(meta['training']['patients'])
    assert tr<=allowed and tr.isdisjoint(excluded)
    assert set(meta['classifier_training']['patients'])<=tr
    b=ledger[meta['base']['key']]
    assert set(b['training']['patients'])==tr
    for fold in meta['crossfit']:
        x=set(fold['train']['patients']);y=set(fold['held']['patients'])
        assert x.isdisjoint(y|excluded) and x|y==tr
        assert set(ledger[fold['base_key']]['training']['patients'])==x
        assert set(fold['train']['ids']).isdisjoint(fold['held']['ids'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    run=Path(args.run).resolve();dest=Path(args.output).resolve()
    freeze=c.readj(run/'freeze.json');views=c.readj(run/'inputs_numeric.json')
    checks={}
    for rel,h in freeze['sources'].items():assert c.sha(c.ROOT/rel)==h
    for name,h in freeze['codes'].items():assert c.sha(run/'source'/name)==h
    checks['sources_and_code_snapshots']=True
    manifest=c.readj(run/'manifest.json')
    for rel,h in manifest['files'].items():assert c.sha(run/rel)==h,rel
    checks['all_output_hashes']=True
    dev=set(c.readj(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']['development'])
    assert {r['sid'] for r in views['main40']}==dev
    assert len(views['main40'])==3675 and len({r['id'] for r in views['main40']})==3675
    assert all({r['sid'] for r in rs}<=dev for rs in views.values())
    checks['development_only_ids']=True
    ledger=c.readj(run/'fits/calibrator_training_ledger.json')
    inner_count=0;maxdiff=0.
    for f in range(4):
        saved=c.readj(run/f'fits/fold{f}.json')
        excluded=set(saved['outer']['held']['patients']);allowed=set(saved['outer']['train']['patients'])
        assert excluded.isdisjoint(allowed) and excluded|allowed==dev
        verify_pipeline(saved['final_pipeline'],allowed,excluded,ledger)
        for inner in saved['inner']:
            tr=set(inner['split']['train']['patients']);te=set(inner['split']['held']['patients'])
            assert tr.isdisjoint(te|excluded) and tr|te==allowed
            verify_pipeline(inner['pipeline'],tr,te|excluded,ledger);inner_count+=1
        with (run/f'fits/fold{f}_inner_predictions.csv').open(encoding='utf-8',newline='') as fh:
            rs=list(csv.DictReader(fh))
        y=np.array([int(r['y']) for r in rs]);v=np.array([int(r['v']) for r in rs]);m=np.array([int(r['m']) for r in rs])
        assert {r['sid'] for r in rs}==allowed
        for kind,field in [('ratio','ratio_selection'),('lr','lr_selection')]:
            s=np.array([float(r[kind]) for r in rs])
            actual=c.select_threshold(y,v,m,s,kind)
            assert actual==saved[field],(f,kind)
        for name,rows in views.items():
            ii=np.array([i for i,r in enumerate(rows) if r['fold']==f]);held=[rows[i] for i in ii]
            if not len(ii):continue
            model=saved['final_pipeline'];ss=c.infer(held,model)
            pred,probs=c.make_outputs(held,ss,saved['ratio_selection']['selected']['threshold'],saved['lr_selection']['selected']['threshold'])
            # Altering held-out labels cannot affect inference.
            flipped=[dict(r,y=(r['y']+1)%3) for r in held]
            changed=c.infer(flipped,model)
            assert all(np.array_equal(ss[k],changed[k]) for k in ss)
            frozen=np.load(run/f'frozen_predictions/{name}.npz')
            for method in c.METHODS:
                assert np.array_equal(pred[method],frozen[method+'_labels'][ii])
                diff=float(np.max(np.abs(probs[method]-frozen[method+'_logprob'][ii])))
                maxdiff=max(maxdiff,diff);assert diff==0.
    checks['nested_patient_isolation']=dict(outer=4,inner=inner_count)
    checks['thresholds_reselected_from_inner_only']=True
    checks['all_parameter_prediction_replays']=dict(max_logprob_difference=maxdiff)
    checks['held_labels_do_not_affect_inference']=True
    for name,rows in views.items():
        data=np.load(run/f'frozen_predictions/{name}.npz');y=np.array([r['y'] for r in rows])
        stored=c.readj(run/name/'metrics.json')
        for method in c.METHODS:
            p=data[method+'_labels'];lp=data[method+'_logprob']
            actual=c.evaluate(c.old.cohort(rows),c.old.predictions(rows,p),profile='research_patient',iterations=1000)
            assert actual==stored['all/'+method]
        for method in c.REPAIRS:
            p=data[method+'_labels'];v=data['Std_V_labels']
            assert np.array_equal(p==0,v==0) and np.all(p[v==1]==1)
            assert np.array_equal(data[method+'_logprob'],data['Std_V_logprob'])
            d=a.transition(rows,v,p)
            assert d['delta_correct']==d['NS_rescued']-d['NA_harmed'] and d['delta_false_S']==0
        pairs=c.readj(run/name/'paired.json')
        for new,old in c.PRIMARY_PAIRS:
            pp=c.paired_compare(c.old.cohort(rows),c.old.predictions(rows,data[old+'_labels']),
                               c.old.predictions(rows,data[new+'_labels']),iterations=1000)
            saved=pairs['all/'+new+'-vs-'+old]
            for key,val in pp.items():assert val==saved[key]
            # Independent patient resampling for PA/MCC class-recall intervals.
            ids=sorted({r['sid'] for r in rows});diffs=[];rec=[]
            for seed in range(1000):
                sample=np.random.RandomState(seed).choice(ids,len(ids),replace=True)
                ix=np.array([i for sid in sample for i,r in enumerate(rows) if r['sid']==sid])
                b=c.cm(y[ix],data[old+'_labels'][ix]);t=c.cm(y[ix],data[new+'_labels'][ix])
                diffs.append(c.metrics_from_confusions(t)-c.metrics_from_confusions(b))
                rec.append([(t[k,k]-b[k,k])/b[k].sum() for k in (1,2)])
            for j,key in enumerate(('PA','AC1','MCC')):
                assert np.allclose(np.quantile(np.array(diffs)[:,j],[.0125,.9875]),saved['extra'][key]['ci97_5'],atol=1e-14)
            for j,key in enumerate(('NS_recall','NA_recall')):
                assert np.allclose(np.quantile(np.array(rec)[:,j],[.025,.975]),saved['extra'][key]['ci95'],atol=1e-14)
    checks['metrics_primary_pairs_and_independent_resampling']=True
    checks['support_probability_preservation_and_swap_identities']=True
    reads=c.readj(run/'read_log.json')
    assert all(not x.startswith('outputs/036_final_validation/') or x.startswith('outputs/036_final_validation/development_001/') for x in reads)
    checks['no_reserved_reads_in_execution_log']=True
    c.put(dest,dict(status='pass',checked_utc=c.now(),checks=checks,n_checks=len(checks),
                   independent_audit=False,API_calls=0,reserved_used=False))
    print('037 verification PASS',len(checks),'checks',flush=True)

if __name__=='__main__':main()
