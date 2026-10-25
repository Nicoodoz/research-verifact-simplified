"""Pre-send empirical token estimates from actual bodies, plus global hard reservation cap."""
from pathlib import Path
import argparse
import math
import numpy as np
import common016 as c

def chars(body):return sum(len(m['content']) for m in body['messages'])

def calibrate():
    result={};sources={}
    for role,task in [('v4_first','010_verifact_baseline_alignment'),('qwen','014_qwen27b_baseline_comparison')]:
        base=c.ROOT/'outputs'/task; jp=base/'preparation_001/jobs.jsonl'; npth=base/'analysis_001/normalized_responses.jsonl'
        jobs={j['request_id']:j for j in c.jsonlines(jp)};ratios=[];outputs=[]
        for n in c.jsonlines(npth):
            if n['status']!='success' or n['request_id'] not in jobs:continue
            j=jobs[n['request_id']];u=n['usage'];ratios.append(u['input_tokens']/chars(j['body']));outputs.append(u['output_tokens'])
        c.require(len(ratios)>=600,'Too little token calibration')
        result[role]=dict(n=len(ratios),token_per_char_p99=float(np.quantile(ratios,.99)),
            token_per_char_max=max(ratios),output_p95=float(np.quantile(outputs,.95)),
            input_factor=float(np.quantile(ratios,.99))*1.10,output_allowance=math.ceil(float(np.quantile(outputs,.95))*1.25))
        sources.update({p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in (jp,npth)})
    return dict(created_utc=c.now(),models=result,sources_sha256=sources,
        exact_server_token_counts_known_before_send=False,method='Historical server tokens / actual message characters; p99 ratio x1.10 +200 input tokens; p95 output x1.25; peak prices, no cache benefit')

def estimate(body,cal):
    q=body['model']==c.QWEN;r=cal['models']['qwen' if q else 'v4_first']
    inp=math.ceil(chars(body)*r['input_factor']+200);out=r['output_allowance']
    return dict(input_tokens_estimate=inp,output_tokens_allowance=out,cny=(inp*3+out*(12 if q else 9))/1e6)

def forecast(jobfile):
    path=Path(jobfile).resolve();cal=c.read(c.OUT/'token_calibration_001.json');c.check_hashes(cal['sources_sha256'])
    jobs=c.jsonlines(path);ledger=c.read(c.OUT/'live/ledger.json') if (c.OUT/'live/ledger.json').exists() else {}
    used=ledger.get('used_or_reserved_cny',0);root=c.OUT/'stage1';prep=root/'preparation_002';prompts=c.read(prep/'judge_prompts.json')
    bp=root/'base_preparation_001';rp=root/'review_preparation_001';records=[]
    def add(j,source):
        e=estimate(j['body'],cal);records.append(dict(request_id=j['request_id'],source=source,body_sha256=c.fingerprint(j['body']),**e))
    if path.parent==rp:
        for j in jobs:add(j,'actual_disagreement_body')
        future=0.
    else:
        if bp.exists():basejobs=c.jsonlines(bp/'jobs.jsonl')
        else:
            basejobs=[dict(request_id='upper:'+item['proposition_id']+role,body=c.judge_body(item,'x'*8400,prompts,role))
                for item in c.jsonlines(prep/'inputs.jsonl') for role in ('v4_first','qwen')]
        for j in basejobs:add(j,'actual_base_body' if bp.exists() else 'C48_character_cap_and_actual_claim')
        # Planning allowance: 30% disagree, versus 12% on 015; not a limit on actual D.
        v4=sum(r['cny'] for r,j in zip(records,basejobs) if j['body']['model']==c.V4)
        future=v4*.30*2*1.10
    current_nonchat=sum(c.bound(j) for j in jobs) if jobs and jobs[0]['kind']!='chat' else 0.
    retrieval_allowance=1.5 if path.parent==prep else current_nonchat
    projected=used+sum(r['cny'] for r in records)+future+retrieval_allowance+3.0
    return dict(created_utc=c.now(),jobfile=path.relative_to(c.ROOT).as_posix(),jobs_sha256=c.file_hash(path),
        used_or_reserved_cny=used,request_token_estimates=records,estimated_chat_cny=sum(r['cny'] for r in records),
        future_disagreement_allowance_cny=future,retrieval_allowance_cny=retrieval_allowance,retry_extra_cny=3.,
        projected_task_total_cny=projected,cap_cny=40,within_cap=projected<=40,
        estimate_not_exact_tokenizer_or_invoice=True,calibration_sha256=c.file_hash(c.OUT/'token_calibration_001.json'),
        price_snapshot_sha256=c.file_hash(c.OUT/'prices_001.json'))

def check_before_send(jobfile):
    digest=c.file_hash(jobfile);p=c.OUT/'budget_checks'/f'{digest}.json';saved=c.read(p)
    c.require(saved['jobs_sha256']==digest and saved['within_cap'] and saved['projected_task_total_cny']<=40,'Projected task exceeds budget')
    c.require(saved['price_snapshot_sha256']==c.file_hash(c.OUT/'prices_001.json') and saved['calibration_sha256']==c.file_hash(c.OUT/'token_calibration_001.json'),'Estimate inputs changed')
    ledger=c.read(c.OUT/'live/ledger.json') if (c.OUT/'live/ledger.json').exists() else {}
    c.require(ledger.get('used_or_reserved_cny',0)<=saved['projected_task_total_cny'],'Re-estimate before continuing unexpected spend')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('jobs',type=Path,nargs='?');a=p.parse_args()
    if a.jobs:
        x=forecast(a.jobs);dst=c.OUT/'budget_checks'/f'{x["jobs_sha256"]}.json';c.write_json(dst,x)
        print(c.canonical({k:v for k,v in x.items() if k!='request_token_estimates'}))
    else:
        x=calibrate();c.write_json(c.OUT/'token_calibration_001.json',x);print(c.canonical(x))
