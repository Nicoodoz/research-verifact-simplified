"""Read-only scientific verification for task 035."""
from __future__ import annotations
import csv, json, hashlib, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(TASK))
import common as c
import analysis as a

OUT=ROOT/'outputs/035_lambda_boundary_calibration'
R1=OUT/'run_001'
R2=OUT/'run_002'
SIX=('U0','U2','U2_T','Joint_NLL','Task_T','Robust_T')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def csvrows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    checks={}
    # 034 official source files were not altered by the 035 renumbering/execution.
    fp=json.loads((OUT/'source_034_fingerprints.json').read_text(encoding='utf-8'))
    bad=[p for p,h in fp.items() if sha(ROOT/p)!=h]
    checks['034_source_fingerprints_unchanged']=not bad
    if bad: raise AssertionError(('034 changed',bad))
    # All frozen scientific inputs still match the run freeze.
    freeze=json.loads((R2/'freeze.json').read_text(encoding='utf-8'))
    for rel,h in freeze['sources'].items():
        if sha(ROOT/rel)!=h:raise AssertionError('input hash mismatch '+rel)
    checks['all_input_hashes_match']=True
    assert freeze['reserved_used'] is False and freeze['new_API_calls']==0
    checks['zero_api_and_no_reserved']=True

    datasets=json.loads((R2/'inputs_numeric.json').read_text(encoding='utf-8'))
    groups=json.loads((ROOT/'outputs/003_error_analysis/patient_groups.json').read_text(encoding='utf-8'))['groups']
    dev=set(groups['development']);reserved=set(groups['reserved_test'])
    main= datasets['main40']
    assert set(r['sid'] for r in main)==dev
    assert not (set(r['sid'] for r in main)&reserved)
    assert len(main)==3675 and len({r['id'] for r in main})==3675
    checks['main40_exact_development_only']=True

    # Prediction freeze content is intact.
    pf=json.loads((R2/'prediction_freeze.json').read_text(encoding='utf-8'))
    for name,h in pf['files'].items():
        if sha(R2/'frozen_predictions'/name)!=h:raise AssertionError('prediction freeze mismatch '+name)
    checks['prediction_freeze_hashes_match']=True
    # Recompute the entire main40 point table from frozen predictions.
    z=np.load(R2/'frozen_predictions/main40.npz')
    stored=json.loads((R2/'main40/metrics.json').read_text(encoding='utf-8'))
    for method in c.METHODS:
        p=z[method+'_labels'];lp=z[method+'_logprob']
        actual=a.point(main,p,lp)
        expected=stored['all/'+method]
        if actual!=expected:raise AssertionError('main40 metric mismatch '+method)
    checks['main40_all_metrics_exact']=True
    assert np.array_equal(z['U2_labels'],z['U2_T_labels'])
    assert np.array_equal(z['U2_labels'],z['Task_T_labels'])
    assert np.array_equal(z['U2_labels'],z['Robust_T_labels'])
    checks['temperature_and_task_rules_preserve_u2_labels']=True

    # Every fold: task/robust selects 2; joint-NLL saturates at upper lambda=4.
    for source in ('old_R0','main40','bridge_deepseek','bridge_qwen'):
        for fold in range(4):
            meta=json.loads((R2/f'fits/{source}/fold{fold}.json').read_text(encoding='utf-8'))
            models=meta['models']
            assert abs(models['Task_T']['lam']-2)<1e-12
            assert abs(models['Robust_T']['lam']-2)<1e-12
            assert abs(models['Joint_NLL']['lam']-4)<1e-12
    checks['all_task_robust_lambda2_and_joint_lambda4']=True
    # run_002 added only exploratory MCC_T; all preregistered six method metrics equal run_001 exactly.
    for dataset in ('old_R0','old_R1','main40','bridge_deepseek','bridge_qwen','DS_to_Q','Q_to_DS'):
        p1=R1/dataset/'metrics.csv';p2=R2/dataset/'metrics.csv'
        if not p1.exists():continue
        r1=csvrows(p1);r2=csvrows(p2)
        r1=[r for r in r1 if r['method'] in SIX]
        r2=[r for r in r2 if r['method'] in SIX]
        if r1!=r2:raise AssertionError('six-method reproduction mismatch '+dataset)
    checks['run002_reproduces_all_run001_six_method_metrics']=True

    # Historical classification anchors.
    anchors={'old_R0':1285,'old_R1':708,'main40':3012}
    for dataset,correct in anchors.items():
        metric=json.loads((R2/dataset/'metrics.json').read_text(encoding='utf-8'))['all/U2']
        cm=np.array(metric['confusion_matrix'])
        assert int(np.trace(cm))==correct
    checks['historical_u2_anchors_match']=True

    result={'status':'pass','checks':checks,'n_checks':len(checks),
            'formal_run':'run_001','exploratory_rerun':'run_002',
            'new_api_calls':0,'reserved_used':False}
    (OUT/'verification_001.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('035 verification PASS',len(checks),'checks')

if __name__=='__main__':main()
