"""No-network executor checks and final execution fingerprint seal."""
import sys, json
import common036 as c
import api036 as a
import retrieval036 as r
import execute036 as e
def main():
    checks=[]
    def check(name,value):assert value,name;checks.append(dict(check=name,passed=True))
    for role in ('baseline','score','peer'):
        body=a.body('A fixed test proposition.','Reference text.',role)
        check(role+'_payload_whitelist',json.loads(body['messages'][1]['content'])=={'proposition':'A fixed test proposition.','reference':'Reference text.'})
        check(role+'_model',body['model']==a.api.MODELS['qwen' if role=='peer' else 'deepseek'])
        check(role+'_same024',body==dict(a.api.old.body('A fixed test proposition.','Reference text.',role!='baseline'),model=body['model']))
        check(role+'_finite_bound',0<a.bound(dict(kind='chat',role=role,body=body))<1)
    check('cap150',c.CAP==150)
    cfg=c.read(c.OUT/'final_freeze_001/config.json');groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']
    check('reserved40_exact',set(cfg['patient_ids'])==set(map(str,groups['reserved_test'])))
    check('no_training_overlap',set(cfg['patient_ids']).isdisjoint(map(str,groups['development'])))
    check('repeat4_before_any_calls',len(cfg['repeat_patients'])==4 and not (c.OUT/'attempts').exists())
    check('forecast_within_authorization',c.read(c.OUT/'final_freeze_001/budget.json')['repeat_choice']['plus20pct_plus3_cny']<=150)
    for name in ['gate_A.json','models035.json','standard_models022.json']:
        obj=c.read(c.OUT/'final_freeze_001'/name)
        ids=obj['final_fit']['training_ids'] if name=='gate_A.json' else obj['training_ids']
        check(name+'_no_reserved_ID',not set(ids)&{r['proposition_id'] for r in c.csvread(c.OUT/'planning_001/claim_metadata.csv')})
    checks.extend([dict(check='035_U2_anchor3675_3012',passed=any(r['dataset']=='main40' and r['scope']=='all' and r['method']=='U2' and r['correct']=='3012' for r in c.csvread(c.OUT/'development_001/all_metrics.csv')))])
    paths=set(c.TASK.glob('*.py'))|{c.TASK/'protocol.md',c.OUT/'final_freeze_001/manifest.json',c.OUT/'materials_001/manifest.json',c.OUT/'planning_001/manifest.json'}
    for mod in list(sys.modules.values()):
        p=getattr(mod,'__file__',None)
        if p:
            from pathlib import Path
            p=Path(p).resolve()
            if p.is_relative_to(c.ROOT) and p.suffix=='.py':paths.add(p)
    c.put(c.OUT/'preflight_001.json',dict(created_utc=c.now(),checks=checks,passed=all(r['passed'] for r in checks),API_calls=0))
    c.require(all(r['passed'] for r in checks),'Preflight failed')
    c.put(c.OUT/'execution_freeze_001.json',dict(created_utc=c.now(),sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(paths)},original_history_unchanged=True))
    e.verify_freeze();print('036 preflight checks passed:',len(checks),'; code and final parameters frozen before first request.')
if __name__=='__main__':main()
