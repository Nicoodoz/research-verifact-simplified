"""One unattended offline process; immutable models/units and atomic status."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import argparse,datetime,sys,traceback
import common030 as c
import analyze030 as a

def execute(out):
    c.offline();manifest=c.verify();config=c.read(c.PREP/'config.json');learn=c.read(c.PREP/'learning_config.json');rows=c.lines(c.PREP/'full_rows.jsonl');features=c.lines(c.PREP/'features.jsonl');sweeps=c.read(c.PREP/'sweeps.json');units=c.lines(c.PREP/'units.jsonl');byunit={u['unit_id']:u for u in units};fullsubjects={r['subject_id'] for r in rows};scope=c.read(c.PREP/'scope.json');models={};completed=0;completed_sweeps=[];started=c.now();total_unique_sweeps=scope['unique_sweeps'];unit_metrics=[];fallbacks=[]
    c.put(out/'input_manifest.json',manifest);c.put(out/'environment.json',c.environment());c.put(out/'config.json',config);c.put(out/'learning_config.json',learn)
    def status(stage):
        c.put(out/'execution_status.json',dict(state='running',stage=stage,started_utc=started,updated_utc=c.now(),pid=os.getpid(),completed_unique_sweeps=len(completed_sweeps),total_unique_sweeps=total_unique_sweeps,completed_patient_method_evaluations=completed,unique_models_saved=len(models),total_unique_models=scope['unique_model_fits'],API_calls=0));print(c.now(),stage,flush=True)
    status('validating frozen inputs; starting predetermined fits')
    for spec in sweeps:
        sid=spec['sweep_id']
        if sid!=spec['canonical_sweep']:
            c.put(out/'sweeps'/sid/'alias.json',dict(canonical_sweep=spec['canonical_sweep'],reason='Identical GT-blind patient schedule; not another independent training experiment'));continue
        base=out/'sweeps'/sid;maps={m:{} for m in config['methods']}
        for uid in spec['units']:
            unit=byunit[uid];train=[r for r in features if r['subject_id'] in unit['train_patients']];test=[r for r in features if r['subject_id']==unit['held_patient']];rr=[r for r in rows if r['subject_id']==unit['held_patient']]
            c.require({r['proposition_id'] for r in train}==set(unit['training_candidate_ids']) and {r['proposition_id'] for r in test}==set(unit['test_candidate_ids']),'Unit ID mismatch')
            for method in config['methods']:
                mid=c.model_id(method,unit['train_patients'])
                if mid not in models:
                    names=c.v.FEATURES[method];fit=c.learning.fold(train,[],names,'Logistic',learn,fullsubjects-set(unit['train_patients']))
                    c.require(fit['final_fit']['training_patients']==unit['train_patients'],'Model training set mismatch');c.require(fit['final_fit']['features']==names,'Feature drift')
                    c.put(out/'models'/f'{mid}.json',dict(model_id=mid,method=method,first_unit=uid,**fit));models[mid]=dict(meta=fit['final_fit'],threshold=fit['threshold'])
                    for f in [fit['final_fit'],*fit['inner_folds']]:
                        if f['fallback']:fallbacks.append(dict(model_id=mid,held_patient=f.get('held_patient'),fallback=f['fallback'],n=f['n'],R=f['R']))
                model=models[mid];c.require(unit['held_patient'] not in model['meta']['training_patients'],'Test patient leaked')
                prob=c.model_probability(model['meta'],test);mapping={r['proposition_id']:dict(subject_id=r['subject_id'],probability=float(p),threshold=model['threshold'],keep=bool(p>=model['threshold']),model_id=mid,train_patients=unit['train_patients']) for r,p in zip(test,prob)}
                c.require(set(maps[method]).isdisjoint(mapping),'Duplicate sweep candidate');maps[method].update(mapping);pred=c.evaluation.pred_for(rr,mapping)
                result=dict(unit=unit,method=method,model_id=mid,candidate_predictions=mapping,full_predictions=[dict(proposition_id=r['proposition_id'],verdict=c.LABELS[int(p)]) for r,p in zip(rr,pred)],metrics=c.point(rr,pred))
                c.put(base/'units'/f'{unit["held_patient"]}_{method}.json',result);unit_metrics.append(dict(sweep_id=sid,bin=spec['bin'],rep=spec['rep'],k=spec['k'],held_patient=unit['held_patient'],method=method,model_id=mid,train_candidates=unit['train_candidates'],train_R=unit['train_R'],train_risk=unit['train_risk'],train_025=unit['train_025'],train_026=unit['train_026'],threshold=model['threshold'],**result['metrics']));completed+=1
            status('fit '+sid+' held='+unit['held_patient'])
        c.require(all(set(mapping)=={r['proposition_id'] for r in features} for mapping in maps.values()),'Incomplete sweep')
        c.put(base/'candidate_predictions.json',maps);a.evaluate_sweep(base/'evaluation',spec,rows,maps)
        if spec['kind']=='size' and spec['k']==14:
            checks={}
            for method in config['methods']:
                previous={r['proposition_id']:r for r in c.read(c.v.OUT/'run_001/patient_OOF'/f'{method}-Logistic'/'predictions.json')}
                checks[method]=all(abs(p['probability']-previous[pid]['probability'])<1e-12 and p['threshold']==previous[pid]['threshold'] and p['keep']==previous[pid]['keep'] for pid,p in maps[method].items())
            c.require(all(checks.values()),'Maximum-size anchor differs from029');c.put(out/'max_size_029_anchor.json',checks)
        completed_sweeps.append(sid);status('completed sweep '+sid)
    c.csvwrite(out/'unit_metrics.csv',unit_metrics);c.put(out/'fallbacks.json',fallbacks);c.put(out/'model_index.json',{mid:dict(training_patients=m['meta']['training_patients'],threshold=m['threshold'],n=m['meta']['n'],R=m['meta']['R'],fallback=m['meta']['fallback']) for mid,m in models.items()})
    c.require(len(models)==scope['unique_model_fits'] and len(completed_sweeps)==total_unique_sweeps,'Incomplete fitting plan')
    status('all fits complete; bootstrap and stability analysis')
    a.aggregate(out,sweeps,units,rows,features,status,config['bootstrap_iterations']);c.verify()
    c.put(out/'integrity_checks.json',dict(all_frozen_inputs_unchanged=True,all_planned_unique_sweeps_completed=True,all_unique_models_saved=True,no_test_patient_in_training=True,noncandidate_U0=True,max_size_029_anchor=True,matched_LP_all_sweeps=True,API_calls=0))
    c.put(out/'execution_status.json',dict(state='completed',started_utc=started,completed_utc=c.now(),pid=os.getpid(),completed_unique_sweeps=len(completed_sweeps),scheduled_sweeps=len(sweeps),unique_models_saved=len(models),completed_patient_method_evaluations=completed,fallback_events=len(fallbacks),errors=[],API_calls=0))
    c.write_text(out/'RUN_STATUS.md','# 030运行状态\n\n全部固定A/B/D、训练规模、患者来源、重新训练稳定性及必要统计已完成。患者隔离、输入指纹、最大规模029锚点及同风险LP核验通过；这是程序自检，不是独立审计或无泄漏的绝对证明。\n\n机器结果见analysis/，每次模型与阈值见models/，每个测试单元及全队列结果见sweeps/；退化fallback见fallbacks.json。未自动生成研究结论、选择winner、扩充材料或启动后续任务。0 API。\n')
    c.put(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(out).as_posix():c.sha(p) for p in out.rglob('*') if p.is_file()}));print('030 completed; stopped without follow-up',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default=datetime.datetime.now().strftime('run_%Y%m%d_%H%M%S'));arg=p.parse_args();c.require(arg.run_id and all(x.isalnum() or x in '_-' for x in arg.run_id),'Invalid run id');out=c.OUT/arg.run_id;out.mkdir(parents=True,exist_ok=False)
    try:execute(out)
    except BaseException as exc:
        error=dict(state='failed',time_utc=c.now(),pid=os.getpid(),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),API_calls=0)
        c.put(out/'errors.json',error);c.put(out/'execution_status.json',error);c.write_text(out/'RUN_STATUS.md','# 030执行失败\n\n已保留全部已完成模型/测试单元和错误现场。查看errors.json和stderr.log。没有自动修改配置、重抽患者或重新启动。\n');traceback.print_exc();return 1
    return 0
if __name__=='__main__':sys.exit(main())
