"""Executor checks; never label these an independent audit."""
import sys,json,subprocess
import numpy as np
import common092 as c
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate
from sklearn.metrics import matthews_corrcoef,accuracy_score,f1_score
def main():
    rows=c.lines(c.OUT/'oof_predictions.jsonl');byid={r['id']:r for r in rows};folds=c.read(c.OUT/'folds.json');checks=[]
    def check(value,name):
        checks.append(dict(name=name,passed=bool(value)))
        if not value:raise AssertionError(name)
    check(len(rows)==9065 and len({r['id'] for r in rows})==9065,'all valid atomic unique');check(len({r['sid'] for r in rows})==100,'all patients')
    master={r['proposition_id']:r for r in c.csvrows(c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv') if r['proposition_type']=='claim' and r['invalid']=='False'}
    check(set(master)=={r['id'] for r in rows},'no cohort exclusions')
    for r in rows:
        f=folds[r['fold']];check(r['sid'] in f['test'] and r['sid'] not in f['train']+f['validation'],'patient isolation '+r['id']);check(r['GT']==master[r['id']]['human_gt'],'unaltered GT '+r['id'])
        for m in ['frozen','finetuned']:
            q=np.asarray(r['probabilities'][m]);check(np.isfinite(q).all() and abs(q.sum()-1)<1e-5 and c.LABELS[int(q.argmax())]==r['predictions'][m],m+' probability '+r['id'])
    tables=c.read(c.OUT/'metrics.json');scopes={'full_OOF':rows,'cached_B_F4_common':[r for r in rows if 'B' in r['predictions'] and 'F4' in r['predictions']]}
    demos={str(e['sid']) for e in c.read(c.ROOT/'outputs/071_judge_icl_feasibility/freeze.json')['examples']};scopes['cached_common_excluding_actual_demo_patients']=[r for r in scopes['cached_B_F4_common'] if r['sid'] not in demos]
    baseline={(r['id'],r['arm']):r for r in c.lines(c.OUT/'cached_baselines.jsonl')};scopes['cached_common_core_valid']=[r for r in scopes['cached_B_F4_common'] if all(baseline[r['id'],arm]['valid'] for arm in ['B','F4'])]
    for scope,tt in tables.items():
        rr=scopes[scope];y=[r['GT'] for r in rr]
        for m,z in tt.items():
            p=[r['predictions'][m] for r in rr];check(abs(matthews_corrcoef(y,p)-z['MCC'])<1e-10,scope+m+' MCC');check(abs(accuracy_score(y,p)-z['PA'])<1e-10,scope+m+' PA');check(abs(f1_score(y,p,labels=c.LABELS,average='macro',zero_division=0)-z['Macro_F1'])<1e-10,scope+m+' MacroF1')
    freeze=c.read(c.OUT/('training_freeze_v3.json' if (c.OUT/'training_freeze_v3.json').exists() else 'training_freeze_v2.json' if (c.OUT/'training_freeze_v2.json').exists() else 'training_freeze.json'))
    for f,h in freeze['code'].items():check(c.sha(c.TASK/f)==h,'frozen code '+f)
    for f in folds:
        for family in ['frozen','finetuned']:
            meta=c.read(c.OUT/f"{family}_fold{f['fold']}"/'complete.json');wp=c.PRIVATE/f"{family}_fold{f['fold']}"/'best.pt';check(c.sha(wp)==meta['weights_sha256'],family+' saved weights');check((meta['encoder_parameter_L2_change']>0)==(family=='finetuned'),family+' encoder trainability')
    for source,h in c.read(c.OUT/'inventory.json')['source_hashes'].items():check(c.sha(c.ROOT/'outputs'/source)==h,'history unchanged '+source)
    changed=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines();check('.gitignore' not in changed,'gitignore unchanged');check(not any((p.startswith('outputs/') or p.startswith('tasks/')) and '/092_task_adapted_verifier/' not in p for p in changed),'no other historical task modification')
    check(c.read(c.OUT/'cloud_training_manifest.json')['training_code_and_config_match_freeze_v3'],'cloud training provenance')
    for r in c.read(c.OUT/'cloud_training_manifest.json')['models']:check(r['weight_sha_match'] and r['strict_load'] and r['finite'] and r['resume_epochs']==5,'transferred '+r['model'])
    for r in c.read(c.OUT/'fusion_models.json'):
        f=folds[r['fold']];check(set(r['training_patients'])<=set(f['train']) and not set(r['training_patients'])&set(f['test']+f['validation']),'fusion patient isolation')
        ids=set(r['training_ids']);check(ids=={p['id'] for p in c.lines(c.OUT/'cached_baselines.jsonl') if p['arm']=='B' and p['valid'] and byid[p['id']]['sid'] in f['train']},'all eligible fusion training IDs')
        check(r['text_weights_sha256']==c.read(c.OUT/f"finetuned_fold{r['fold']}"/'complete.json')['weights_sha256'],'fusion uses same-fold model')
        check(0<=r['fits']['text_fusion']['parameters'][2]<=4,'fusion alpha bound')
    fr=c.lines(c.OUT/'fusion_predictions.jsonl');check(len(fr)==956 and len({r['id'] for r in fr})==956,'fusion coverage')
    for m,z in c.read(c.OUT/'fusion_supplement.json')['metrics'].items():
        check(abs(matthews_corrcoef([r['GT'] for r in fr],[r['predictions'][m] for r in fr])-z['MCC'])<1e-10,'fusion MCC '+m)
    for r in fr:
        if not r['fusion_baseline_valid']:check(r['predictions']['B']==r['predictions']['bias_only']==r['predictions']['text_fusion'],'invalid B preserved')
    check(c.read(c.OUT/'costs.json')['API_cost_cny']==0,'zero API')
    for p in list(c.TASK.rglob('*'))+list(c.OUT.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:continue
        check(p.stat().st_size<50_000_000,'public size '+p.name)
        if p.suffix=='.jsonl':
            for r in c.lines(p):check(not any(k in r for k in ['text','reference','claim','content','reasoning_content','input_ids']),'no clinical fields '+p.name)
    c.put(c.OUT/'selfcheck.json',dict(status='PASS',executor_selfcheck=True,independent_audit=False,checks=len(checks),failed=0,summary='ID/GT/isolation/metrics/checkpoints/frozen source/privacy/cost',utc=c.now()))
    print('Executor checks PASS',len(checks),flush=True)
if __name__=='__main__':main()
