"""Train/freeze only on024 patients, bind019 inputs and all possible request templates."""
import shutil,subprocess
import common026 as c
def seal(folder,deps):
    c.put(folder/'manifest.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in list(folder.iterdir())+deps if p.is_file()}))
def run():
    c.require(not (c.OUT/'attempts').exists(),'Must freeze before026 outputs')
    source=c.ROOT/'outputs/025_lambda_flip_risk_separability';path=source/'preparation_001/rows.jsonl';m=c.read(source/'preparation_001/manifest.json');c.require(c.sha(path)==m['sha256'][path.relative_to(c.ROOT).as_posix()],'025 training input changed')
    train=[r for r in c.lines(path) if r['group']=='024_D' and r['candidate']];c.require(len(train)==103,'Expected103 training candidates')
    names=c.risk.METHODS['SD'];threshold,inner=c.learning.training_threshold(train,names);predict,gate=c.learning.fit(train,names)
    gate.update(threshold=float(threshold),training_rule='025 full-development final fit; internal patient-LOPO 80%R threshold',parameters=dict(C=.1,solver='lbfgs',max_iter=2000,tol=1e-8,penalty='l2'),inner_folds=inner,lambda_value=2)
    c.require(not gate['constant_fallback'],'Unexpected single class training')
    for r,p in zip(train,predict(train)):
        x=c.np.array([r['features'][n] for n in names]);manual=float(c.expit(((x-c.np.array(gate['mean']))/c.np.array(gate['scale']))@c.np.array(gate['coef'])+gate['intercept']));c.require(abs(manual-float(p))<1e-12,'Inference differs from training implementation')
    gf=c.OUT/'gate_freeze';gf.mkdir(parents=True);c.put(gf/'gate.json',gate)
    deps=[path,source/'preparation_001/manifest.json',c.ROOT/'tasks/025_lambda_flip_risk_separability/learning025.py',c.ROOT/'tasks/025_lambda_flip_risk_separability/common025.py',c.TASK/'common026.py',c.OUT/'protocol_001.md']
    seal(gf,deps)
    old=c.ROOT/'outputs/019_support_boundary_screen/selection';ip=old/'preparation/inputs.jsonl';cp=old/'cohort.csv';mat=c.lines(ip);rows=c.csvread(cp)
    oldman=c.read(old/'preparation/manifest.json')['sha256'];c.require(c.sha(ip)==oldman[ip.relative_to(c.ROOT).as_posix()],'019 evidence changed')
    c.require(len(rows)==len(mat)==650 and set(r['subject_id'] for r in rows).isdisjoint(gate['training_patients']),'Validation patient overlap')
    prep=c.OUT/'preparation_001';prep.mkdir();shutil.copyfile(cp,prep/'cohort.csv');shutil.copyfile(ip,prep/'inputs.jsonl');jobs=[]
    for r in mat:
        for model,arm in [('deepseek','S'),('deepseek','B'),('qwen','S')]:
            body=c.api.old.body(r['text'],r['reference'],arm=='S');body['model']=c.MODELS[model]
            rid=c.fingerprint(['026',r['proposition_id'],model,arm])[:24];jobs.append(dict(request_id=rid,proposition_id=r['proposition_id'],model_key=model,arm=arm,body=body))
    jobs.sort(key=lambda j:c.fingerprint('026/order/'+j['request_id']))
    with (prep/'jobs_all.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for j in jobs:f.write(c.canonical(j)+'\n')
    oldnorm=c.lines(old/'analysis_001/normalized.jsonl');d_cost=sum((r['usage']['prompt_tokens']*3+r['usage']['completion_tokens']*9)/1e6 for r in oldnorm)
    qnorm=[r for r in c.lines(c.ROOT/'outputs/024_lambda2_transfer_validation/analysis_001/normalized.jsonl') if r['model_key']=='qwen' and r['arm']=='S'];q_mean=sum((r['usage']['prompt_tokens']*3+r['usage']['completion_tokens']*12)/1e6 for r in qnorm)/len(qnorm)
    q_worst=650*q_mean;expected=d_cost+130*q_mean;high=d_cost+q_worst;c.require(high*1.3<80,'Estimated task exceeds cap')
    cfg=c.load_config(c.ROOT/'.env.aliyun')
    c.put(prep/'registry.json',dict(created_utc=c.now(),models=c.MODELS,endpoint=cfg.endpoint,price_checked_date='2026-09-19',prices_cny_per_million=c.api.PRICES,price_sources=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://help.aliyun.com/zh/model-studio/qwen3-8-27b'],price_basis='Beijing peak/no cache; not bill',validation_claims=650,validation_patients=sorted(set(r['subject_id'] for r in rows)),deepseek_B_S_requests=1300,qwen_rule='valid Dscore U0!=S and U2=S only',expected_per_request=dict(deepseek=d_cost/1300,qwen=q_mean),expected_cost_at20pct_candidates=expected,all650_candidate_expected_cost=high,all650_candidate_plus30pct=high*1.3,cap_cny=80,transport='024 task-local direct HTTPS, OS proxy unchanged',git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()))
    code=list(c.TASK.glob('*.py'))+[c.ROOT/'tasks/024_lambda2_transfer_validation/core024.py',c.ROOT/'tasks/024_lambda2_transfer_validation/transport_direct024.py',c.ROOT/'tasks/019_support_boundary_screen/common019.py',c.api.old.prior.PROMPTS]
    seal(prep,[ip,cp,old/'preparation/manifest.json',gf/'manifest.json',c.OUT/'protocol_001.md']+code)
    print(c.canonical(dict(threshold=threshold,training_candidates=103,expected_cost=expected,all_candidates_plus30pct=high*1.3)))
if __name__=='__main__':run()
