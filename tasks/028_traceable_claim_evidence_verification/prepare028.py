"""Freeze all155 candidate inputs and both arms before any028 service response."""
import subprocess
from pathlib import Path
import common028 as c
def run():
    c.require(not (c.OUT/'attempts').exists(),'Freeze first');source=c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002';manifest=c.read(source/'manifest.json');c.require(all(c.sha(source/n)==h for n,h in manifest['outputs'].items()),'027 changed')
    candidates=c.read(source/'candidates.json');c.require(len(candidates)==155,'Candidate count')
    oldjobs=c.lines(c.ROOT/'outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl');oldmat={j['proposition_id']:c.json.loads(j['body']['messages'][1]['content']) for j in oldjobs if j['model_key']=='deepseek' and j['arm']=='S'}
    newmat={r['proposition_id']:dict(proposition=r['text'],reference=r['reference']) for r in c.lines(c.ROOT/'outputs/026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl')};jobs=[];materials=[]
    for r in candidates:
        payload=(oldmat if r['group']=='025' else newmat)[r['proposition_id']];materials.append(dict(proposition_id=r['proposition_id'],group=r['group'],text=payload['proposition'],reference=payload['reference']))
        for arm in ('repeat','trace'):
            b=c.body(payload['proposition'],payload['reference'],arm);jobs.append(dict(request_id=c.fingerprint(['028',r['group'],r['proposition_id'],arm])[:24],group=r['group'],proposition_id=r['proposition_id'],model_key='deepseek',arm=arm,body=b))
    jobs.sort(key=lambda r:c.fingerprint('028/order/'+r['request_id']));worst=sum(c.bound(j) for j in jobs);c.require(worst<80,'Conservative all-jobs cost exceeds budget')
    out=c.OUT/'preparation_001';out.mkdir(parents=True,exist_ok=False);c.put(out/'candidates.json',candidates)
    for name,rows in [('jobs',jobs),('materials',materials)]:
        with (out/(name+'.jsonl')).open('x',encoding='utf-8',newline='\n') as f:
            for r in rows:f.write(c.canonical(r)+'\n')
    cfg=c.api.load_config(c.ROOT/'.env.aliyun');client=c.DirectClient(c.api.Config(cfg.api_key,cfg.base_url,c.MODEL))
    for j in jobs:client.validate(j['body'])
    c.put(out/'registry.json',dict(created_utc=c.now(),model=c.MODEL,endpoint=cfg.endpoint,price_checked_date='2026-09-19',prices_cny_per_million=[3,9],price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash#snapshot-deepseek-v4-flash-0731',price_basis='0731 Beijing peak/no cache; not generic alias1/2; not bill',all310_conservative_reservation_cny=worst,rough_expected_cny=sum((len(c.canonical(j['body']).encode())/3*3+(1200 if j['arm']=='trace' else 350)*9)/1e6 for j in jobs),input_estimate='exact frozen UTF8 bytes /3 for rough mean; bytes+2000 for reservation',cap_cny=80,requests=310,candidates_by_group={'025':103,'026':52},settings=dict(temperature=0,max_tokens=4096,enable_thinking=False,n=1,stream=False),transport='024 direct HTTPS implementation; no OS proxy change',git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()))
    deps=[source/'manifest.json',source/'candidates.json',c.ROOT/'outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl',c.ROOT/'outputs/026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl',c.OUT/'protocol_001.md',c.ROOT/'tasks/024_lambda2_transfer_validation/core024.py',c.ROOT/'tasks/024_lambda2_transfer_validation/transport_direct024.py',c.api.old.prior.PROMPTS]+list(c.TASK.glob('*.py'))+list(out.iterdir())
    c.put(out/'manifest.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps if p.is_file()}));print(c.canonical(c.read(out/'registry.json')))
if __name__=='__main__':run()
