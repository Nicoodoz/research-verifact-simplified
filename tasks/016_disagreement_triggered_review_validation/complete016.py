"""Continue016 with Alibaba Qwen and SiliconFlow V4; one cumulative40 CNY budget."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from copy import deepcopy
import argparse
import json
import math
import time
import os
import common016 as c
from completion_io016 import ORIGINAL,OUT,ALI_MODEL,collect,answers,bound,charge
from verifact_research.inference.aliyun import load_config,AliyunClient

def prepare():
    c.require(not OUT.exists(),'Continuation exists')
    for name in ('handoff_001.json','recovery_001/handoff_001.json','v4_completion_001/handoff_001.json','finalization_001/handoff_002.json'):
        c.check_hashes(c.read(ORIGINAL/name)['files_sha256'])
    values,attempts,total=collect(False);a,prov=answers(values)
    c.require(sum(k[1]=='qwen' for k in a)==128 and sum(k[1]=='v4_first' for k in a)==601,'Checkpoint coverage changed')
    jobs=[]
    for old in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl'):
        if old['role']!='qwen' or (old['proposition_id'],'qwen') in a:continue
        body=deepcopy(old['body']);body['model']=ALI_MODEL
        jobs.append(dict(old,body=body,request_id='016:aliyun:'+c.fingerprint(body)))
    c.require(len(jobs)==473,'Missing count changed');OUT.mkdir();(OUT/'base').mkdir();(OUT/'live').mkdir()
    c.write_lines(OUT/'base/jobs.jsonl',jobs);c.write_csv(OUT/'base/retained_provenance.csv',prov)
    config=load_config(c.ROOT/'.env.aliyun')
    c.require(config.model==ALI_MODEL and config.api_key,'Alibaba config missing')
    c.write_json(OUT/'protocol_amendment.json',dict(created_utc=c.now(),user_authorization='Complete existing016 using Alibaba for missing Qwen; original gates,601 cohort and40 total cap',
        original_protocol_sha256=c.file_hash(ORIGINAL/'protocol_002.md'),gate_code_sha256=c.file_hash(c.TASK/'decisions016.py'),
        prior_cny=total,cap_cny=40,V4_retained=601,Qwen_SiliconFlow_retained=127,Qwen_Alibaba_probe_retained=1,Qwen_missing=473,
        Alibaba_endpoint=config.endpoint,Alibaba_model=ALI_MODEL,V4_endpoint=c.NATIVE.ENDPOINTS['chat'],V4_model=c.V4,
        change='Only remaining Qwen provider and model API identifier; exact other body fields preserved; preserve successful probe',
        limitation='Qwen baseline mixes suppliers127/474 and baseline periods differ. Not immutable equivalent weights, not strict contemporaneous pure-model comparison.',
        no_GT_for_selection_or_trigger=True,no_new_patients_or_methods=True,repeat_review_only_on_disagreements=True,
        first_batch=8,later_batch_max=48,workers=4,reestimate_each_batch=True,service_error_halts_new_dispatch=True,
        max_attempts_per_new_job=2,received200_never_regenerated=True,unknown_reservations_always_carried=True,
        next_stage_not_authorized=True))
    c.write_json(OUT/'prices.json',dict(checked_date='2026-09-16',Alibaba_source='https://help.aliyun.com/zh/model-studio/qwen3-8-27b',Alibaba_input_output=[3,12],
        SF_source='https://docs.siliconflow.cn/docs/release-notes/overview',SF_peak_input_output=[3,9],SF_cache=.3,
        unit='CNY per million tokens',Alibaba_cache_discount_not_assumed=True))
    code=c.execution_code()+[Path(__file__),c.TASK/'completion_io016.py',c.TASK/'finish_io016.py',c.ROOT/'src/verifact_research/inference/aliyun.py']
    c.write_json(OUT/'authority.json',dict(approved=True,task_cap_cny=40,execution_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},protocol_sha256=c.file_hash(OUT/'protocol_amendment.json')))
    c.seal(OUT/'base',[ORIGINAL/'stage1/base_preparation_001/manifest.json',OUT/'protocol_amendment.json'],code)
    c.write_json(OUT/'live/ledger.json',dict(carry_cny=total,used_or_reserved_cny=total,exhausted_accounts=[],phases={}))
    print(c.canonical(dict(Qwen_to_complete=len(jobs),prior_cny=total)))

def forecast(phase):
    values,attempts,total=collect();a,_=answers(values)
    jobs=c.jsonlines(OUT/phase/'jobs.jsonl');pending=[j for j in jobs if (j['proposition_id'],j['role']) not in a]
    cal=c.read(ORIGINAL/'token_calibration_001.json')['models']
    def estimate(j):
        q=j['role']=='qwen';p=cal['qwen' if q else 'v4_first'];inp=math.ceil(sum(len(m['content']) for m in j['body']['messages'])*p['input_factor']+200)
        return (inp*3+p['output_allowance']*(12 if q else 9))/1e6
    expected=sum(estimate(j) for j in pending)
    future=sum(estimate(j) for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl') if j['role']=='v4_first')*.30*2*1.10 if phase=='base' else 0
    recent=[x for x in attempts if x['epoch']=='completion_002' and x['phase']==phase][-48:]
    good=sum(x['http_status']==200 for x in recent);bad=[x for x in recent if x['http_status'] not in (200,402)]
    margin=max(2.,sum(x['charge_cny'] for x in bad)/max(1,good)*len(pending));projected=total+expected+future+margin
    record=dict(created_utc=c.now(),phase=phase,pending=len(pending),prior_cny=total,remaining_estimate_cny=expected,future_reviews_cny=future,
        failure_margin_cny=margin,projected_total_cny=projected,cap_cny=40,within_cap=projected<=40 and not (bad and not good),
        actual_jobs_sha256=c.file_hash(OUT/phase/'jobs.jsonl'),price_sha256=c.file_hash(OUT/'prices.json'),
        token_estimate='Actual message chars, original historical server p99 ratio x1.10+200; output p95x1.25; not exact Alibaba tokenizer')
    folder=OUT/'budgets';folder.mkdir(exist_ok=True);c.write_json(folder/f'estimate_{len(list(folder.glob("*.json")))+1:03d}.json',record)
    print(c.canonical(record),flush=True);c.require(record['within_cap'],'Whole016 forecast exceeds40 or service uncertain')
    return pending

def send(phase,limit):
    c.require(1<=limit<=48 and not (OUT/'analysis_001').exists(),'Invalid limit or already analyzed')
    c.check_hashes(c.read(OUT/'authority.json')['execution_sha256']);c.check_manifest(OUT/phase)
    pending=forecast(phase)
    if not pending:return
    jobs=c.jsonlines(OUT/phase/'jobs.jsonl');digest=c.file_hash(OUT/phase/'jobs.jsonl')
    config=load_config(c.ROOT/'.env.aliyun');amend=c.read(OUT/'protocol_amendment.json')
    c.require(config.endpoint==amend['Alibaba_endpoint'] and config.model==ALI_MODEL,'Alibaba endpoint changed')
    accounts=[a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    c.require(accounts and accounts[0].alias=='account_2','Account pool order changed')
    ledgerpath=OUT/'live/ledger.json';ledger=c.read(ledgerpath);lock=OUT/'task_api.lock'
    c.require(not ledger.get('bound_violation'),'Prior reservation bound violation must be reviewed')
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        folder=OUT/'live'/phase;folder.mkdir(exist_ok=True)
        state=ledger['phases'].setdefault(phase,dict(jobs_sha256=digest,jobs={j['request_id']:dict(status='pending',receipts=[],attempts=0) for j in jobs}))
        c.require(state['jobs_sha256']==digest,'Jobs changed');c.require(all(p['status']!='in_flight' for p in state['jobs'].values()),'Inspect interrupted run; do not resend unknown')
        c.save(ledgerpath,ledger);ali=AliyunClient(config);sf=c.NATIVE.HttpClient();sent=0;halt=False;last=time.monotonic()
        def perform(j,account,attempt):
            start=c.now()
            try:tr=ali.send(j['body']) if phase=='base' else sf.send(account,j)
            except Exception:tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=start,ended_utc=c.now())
            safe=c.canonical(tr)
            for key in [config.api_key]+[a.key for a in accounts]:safe=safe.replace(json.dumps(key,ensure_ascii=False)[1:-1],'[REDACTED_API_KEY]')
            return dict(request_id=j['request_id'],job_sha256=c.fingerprint(j),jobs_sha256=digest,attempt=attempt,
                account='aliyun_main' if phase=='base' else account.alias,provider='aliyun' if phase=='base' else 'siliconflow',
                endpoint=config.endpoint if phase=='base' else c.NATIVE.ENDPOINTS['chat'],transport=json.loads(safe))
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={}
            while True:
                account=next((x for x in accounts if x.alias not in ledger['exhausted_accounts']),None)
                if not halt and (phase=='base' or account):
                    for i,j in enumerate(jobs):
                        p=state['jobs'][j['request_id']]
                        if len(futures)>=4 or sent>=limit:break
                        if p['status'] not in ('pending','retry') or p['attempts']>=2:continue
                        if ledger['used_or_reserved_cny']+bound(j)>40:halt=True;break
                        ledger['used_or_reserved_cny']+=bound(j);p.update(status='in_flight',attempts=p['attempts']+1,started_utc=c.now())
                        c.save(ledgerpath,ledger);futures[pool.submit(perform,j,account,p['attempts'])]=(i,j);sent+=1
                if not futures:break
                done,_=wait(futures,timeout=1,return_when=FIRST_COMPLETED)
                for f in done:
                    i,j=futures.pop(f);r=f.result();p=state['jobs'][j['request_id']];tr=r['transport'];fee,basis=charge(j,tr)
                    file=folder/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json';c.write_json(file,r)
                    p['receipts'].append(dict(file=file.relative_to(OUT).as_posix(),sha256=c.file_hash(file),charge_cny=fee,charge_basis=basis))
                    ledger['used_or_reserved_cny']+=fee-bound(j)
                    if tr['http_status']==200:
                        p['status']='received';n=c.old14.normalize(j,r,model=j['body']['model'])
                        if n['status']!='success':halt=True
                    elif phase=='review' and c.balance_exhausted(tr):
                        p['status']='retry';ledger['exhausted_accounts'].append(r['account'])
                    else:p['status']='retry' if p['attempts']<2 else 'failed';halt=True
                    if fee>bound(j)+1e-10:halt=True;ledger['bound_violation']=True
                    c.save(ledgerpath,ledger)
                if time.monotonic()-last>=30:
                    print(phase,'received',sum(p['status']=='received' for p in state['jobs'].values()),'/',len(jobs),'task_budget',round(ledger['used_or_reserved_cny'],4),flush=True);last=time.monotonic()
        print(c.canonical(dict(phase=phase,sent_this_batch=sent,received=sum(p['status']=='received' for p in state['jobs'].values()),total_jobs=len(jobs),used_cny=ledger['used_or_reserved_cny'],halt=halt)),flush=True)
    finally:lock.unlink()
    values,_,_=collect();answers(values)

def review():
    values,attempts,total=collect();a,prov=answers(values,True);prep=OUT/'review';c.require(not prep.exists(),'Review already frozen');prep.mkdir()
    prompts=c.read(ORIGINAL/'stage1/preparation_002/judge_prompts.json');jobs=[];triggers=[]
    for item in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/inputs.jsonl'):
        pid=item['proposition_id'];v=a[(pid,'v4_first')]['verdict'];q=a[(pid,'qwen')]['verdict'];d=v!=q
        triggers.append(dict(proposition_id=pid,v4_first=v,qwen=q,disagreement=d))
        if not d:continue
        for role in ('v4_repeat','independent_review'):
            body=c.judge_body(item,item['reference'],prompts,role)
            jobs.append(dict(request_id=f'016:stage1:{role}:'+c.fingerprint(body),kind='chat',role=role,proposition_id=pid,case_id=item['case_id'],body=body))
    c.require(len(jobs)==len({j['request_id'] for j in jobs}),'Duplicate review bodies need explicit assignment mapping')
    jobs.sort(key=lambda j:c.hash_rank(j['request_id'],'016/review-send/v1:'))
    c.write_lines(prep/'jobs.jsonl',jobs);c.write_csv(prep/'trigger.csv',triggers);c.write_csv(prep/'base_provenance.csv',prov)
    c.write_json(prep/'base_ledger_snapshot.json',c.read(OUT/'live/ledger.json'))
    c.write_json(prep/'summary.json',dict(claims=601,disagreements=sum(r['disagreement'] for r in triggers),calls=len(jobs),GT_used=False))
    c.seal(prep,[ORIGINAL/'stage1/base_preparation_001/manifest.json',OUT/'protocol_amendment.json'],[Path(__file__),c.TASK/'completion_io016.py',c.TASK/'common016.py'])
    print(c.canonical(c.read(prep/'summary.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','send','forecast','review'));p.add_argument('--phase',choices=('base','review'),default='base');p.add_argument('--limit',type=int,default=48);a=p.parse_args()
    if a.action=='send':send(a.phase,a.limit)
    elif a.action=='forecast':forecast(a.phase)
    else:globals()[a.action]()
