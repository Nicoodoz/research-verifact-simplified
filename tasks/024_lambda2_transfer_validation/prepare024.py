"""Freeze all 879 previously exposed claims before any new API output."""
import shutil,subprocess
from collections import Counter
import common024 as c
def run():
    out=c.OUT/'preparation_001';out.mkdir(parents=True,exist_ok=False)
    prior=c.ROOT/'outputs/020_lambda2_patient_validation'
    cp=prior/'new10/preparation_002/cohort.csv';ip=prior/'new10/base_preparation_001/inputs.jsonl'
    c.old.check_manifest(cp.parent);c.old.check_manifest(ip.parent)
    rows=c.csvread(cp);ins=c.lines(ip);byid={x['proposition_id']:x for x in ins}
    c.require(len(rows)==len(byid)==879,'Full frozen cohort required')
    shutil.copyfile(cp,out/'cohort.csv')
    jobs=[]
    for r in rows:
        x=byid[r['proposition_id']]
        for model in c.MODELS:
            for arm in ('B','S'):
                body=c.old.body(x['text'],x['reference'],arm=='S');body['model']=c.MODELS[model]
                rid=c.fingerprint([r['proposition_id'],model,arm])[:24]
                jobs.append(dict(request_id=rid,proposition_id=r['proposition_id'],model_key=model,arm=arm,body=body))
    jobs.sort(key=lambda j:c.fingerprint('024/order/v1:'+j['request_id']))
    with (out/'jobs.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for j in jobs:f.write(c.canonical(j)+'\n')
    hist=[r for r in c.lines(prior/'analysis_001/normalized.jsonl') if r['repeat']==0]
    ti=sum(r['usage']['prompt_tokens'] for r in hist);to=sum(r['usage']['completion_tokens'] for r in hist)
    estimate={k:(ti*p[0]+to*p[1])/1e6 for k,p in c.PRICES.items()}
    c.require(sum(estimate.values())*1.3<c.CAP,'Expected task exceeds cap')
    cfg=c.load_config(c.ROOT/'.env.aliyun')
    c.put(out/'registry.json',dict(created_utc=c.now(),models=c.MODELS,endpoint=cfg.endpoint,prices_cny_per_million=c.PRICES,price_basis='Beijing peak, no cache discounts; not billing reconciliation',price_sources=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://help.aliyun.com/zh/model-studio/qwen3-8-27b'],verified_date='2026-09-19',settings={k:v for k,v in jobs[0]['body'].items() if k not in ('messages','response_format','model')},claims=879,patients=10,authors=dict(Counter(r['author_type'] for r in rows)),gt_counts=dict(Counter(r['human_gt'] for r in rows)),requests=len(jobs),historical_r0_usage=dict(input_tokens=ti,output_tokens=to),expected_cny=estimate,expected_plus30percent_cny=sum(estimate.values())*1.3,cap_cny=80,rounds_per_model=1,qwen_immutable_snapshot_available=False,reserved_used=False))
    deps=[cp,ip,prior/'analysis_001/normalized.jsonl',c.old.prior.PROMPTS,c.ROOT/'tasks/019_support_boundary_screen/common019.py',c.ROOT/'tasks/020_lambda2_patient_validation/common020.py',c.ROOT/'src/verifact_research/inference/aliyun.py',c.OUT/'protocol_001.md']+list(c.TASK.glob('*.py'))
    paths=list(out.glob('*'))+deps
    c.put(out/'manifest.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths}))
    print(c.canonical(dict(requests=len(jobs),expected=estimate,plus30percent=sum(estimate.values())*1.3)))
if __name__=='__main__':run()
