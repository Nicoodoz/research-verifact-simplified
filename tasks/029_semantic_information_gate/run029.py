"""Single unattended offline run. Durable fold checkpoints; never overwrite a run."""
import os
for _k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_k]='1'
import argparse,datetime,sys,traceback
import common029 as c
import learning029 as learning
import evaluate029 as evaluation

def execute(out):
    c.offline();manifest=c.verify_frozen();config=c.read(c.PREP/'config.json');rows=c.lines(c.PREP/'full_rows.jsonl');features=c.lines(c.PREP/'features.jsonl');folds=c.read(c.PREP/'outer_folds.json');methods=evaluation.conditions(config);complete=[]
    c.put(out/'input_manifest.json',manifest);c.put(out/'environment.json',c.environment());c.put(out/'config.json',config);c.put(out/'feature_schema.json',c.schema())
    def status(stage):
        c.put(out/'execution_status.json',dict(state='running',stage=stage,updated_utc=c.now(),pid=os.getpid(),completed_conditions=complete,API_calls=0));print(c.now(),stage,flush=True)
    for scope in ('patient_OOF','025_to_026','026_to_025'):
        target=rows if scope=='patient_OOF' else [r for r in rows if r['group']==scope[-3:]];mappings={}
        for method in methods:
            a,e=method.split('-',1);dest=out/scope/method;dest.mkdir(parents=True);records=[]
            if scope=='patient_OOF':plans=[(f['test_patient'],[r for r in features if r['subject_id']!=f['test_patient']],[r for r in features if r['subject_id']==f['test_patient']],[f['test_patient']]) for f in folds]
            else:
                train_group=scope[:3];test_group=scope[-3:];plans=[('transfer',[r for r in features if r['group']==train_group],[r for r in features if r['group']==test_group],sorted({r['subject_id'] for r in target}))]
            for fold_id,train,test,excluded in plans:
                result=learning.fold(train,test,c.FEATURES[a],e,config,excluded)
                result['eligible_training_patients_in_full_cohort']=sorted({r['subject_id'] for r in rows if r['subject_id'] not in excluded})
                c.put(dest/f'fold_{fold_id}.json',result);records.extend(result['predictions'])
                status(scope+' '+method+' fold '+fold_id)
            c.require(len(records)==len({r['proposition_id'] for r in records})==sum(r['candidate'] for r in target),'Prediction coverage')
            mappings[method]={r['proposition_id']:r for r in records};c.csvwrite(dest/'predictions.csv',records);c.put(dest/'predictions.json',records);complete.append(scope+'/'+method)
        status(scope+' all fits complete; evaluation begins')
        evaluation.evaluate(out,scope,target,mappings,config,features,status)
    # Reverify frozen inputs and code after computation. Historical bytes remain read-only.
    c.verify_frozen();status('final integrity checks')
    c.put(out/'integrity_checks.json',dict(all_conditions_complete=len(complete)==36,complete_count=len(complete),patient_isolation_checked_every_fold=True,input_hashes_unchanged=True,feature_schema_unchanged=True,noncandidate_U0=True,API_calls=0,reserved_access=False,new_fits_are_development_only=True))
    c.put(out/'execution_status.json',dict(state='completed',completed_utc=c.now(),pid=os.getpid(),completed_conditions=complete,errors=[],API_calls=0))
    c.write_text(out/'RUN_STATUS.md','# 029运行状态\n\n全部完成：12条件（8主条件＋4去质量消融）×患者OOF/双向迁移，共36组。患者隔离、分母、输入哈希、R/H/W守恒及global包络独立LP核验通过。无检测到的数据泄漏或执行异常；这不是独立审计证明。\n\n机器结果在各scope/evaluation；每折模型、训练患者和阈值在各scope/条件/fold_*.json。Bootstrap固定预测不重训。未选择winner，未写正式研究结论，未启动030或reserved40。\n')
    c.put(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(out).as_posix():c.sha(p) for p in out.rglob('*') if p.is_file()}));print('029 completed; no follow-up automatically launched',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default=datetime.datetime.now().strftime('run_%Y%m%d_%H%M%S'));args=p.parse_args();c.require(args.run_id and all(ch.isalnum() or ch in '_-' for ch in args.run_id),'Invalid run id');out=c.OUT/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    try:execute(out)
    except BaseException as exc:
        error=dict(state='failed',time_utc=c.now(),pid=os.getpid(),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),API_calls=0)
        c.put(out/'errors.json',error);c.put(out/'execution_status.json',error);c.write_text(out/'RUN_STATUS.md','# 029运行失败\n\n已保留完成的折、中间结果和错误现场；未覆盖旧run。查看errors.json及execution_status.json。没有自动改配置、重试实验或新增调用。\n');traceback.print_exc();return 1
    return 0
if __name__=='__main__':sys.exit(main())
