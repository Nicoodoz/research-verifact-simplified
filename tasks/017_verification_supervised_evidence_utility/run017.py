"""Durable017 transport: one80 CNY task ledger; SF pool then registered Alibaba V4."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from dataclasses import replace
import argparse,json,math,os,time
import common017 as c
from verifact_research.inference.aliyun import load_config,AliyunClient

ALI_MODEL='deepseek-v4-flash-0731'
GLOBAL_ROUTE=c.ROOT/'outputs/service_tools/provider_routing/current.json'

def bound(job):return c.old.NATIVE.bound(job)
def cost(job,tr):
    if job['body']['model']!=ALI_MODEL:return c.old.NATIVE.cost(job,tr)
    try:
        u=c.old.sf.normalize_usage(c.old.pilot.strict_json(tr['body_text']))
        c.require(u['total_tokens']==u['input_tokens']+u['output_tokens'],'Invalid usage')
        return (u['input_tokens']*3+u['output_tokens']*9)/1e6,'Alibaba_V4_0731_peak_no_cache_estimate_not_invoice'
    except (ValueError,KeyError,TypeError,IndexError):return bound(job),'unknown_usage_reservation'
def authorize():
    c.check(c.OUT/'preparation_001');summary=c.read(c.OUT/'preparation_001/summary.json')
    c.require(summary['all_stage_planning_estimate_cny']<=80,'Whole conditional plan exceeds80')
    code=c.old.execution_code()+[c.TASK/n for n in ('common017.py','selection017.py','prepare017.py','gate017.py','run017.py')]+[c.ROOT/'src/verifact_research/inference/aliyun.py']
    c.write_json(c.OUT/'authority_001.json',dict(created_utc=c.now(),authorization='User017 request plus80 CNY whole-task standing rule',cap_cny=80,
        execution_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},protocol_sha256=c.file_hash(c.OUT/'protocol_001.md'),
        execution_policy_sha256=c.file_hash(c.OUT/'execution_policy_001.json'),planning_estimate_cny=summary['all_stage_planning_estimate_cny'],
        SF_model=c.MODEL,Alibaba_fallback_model=ALI_MODEL,Alibaba_endpoint=load_config(c.ROOT/'.env.aliyun').endpoint,prices_sources=['https://docs.siliconflow.cn/docs/release-notes/overview','https://help.aliyun.com/zh/model-studio/deepseek-v4-flash'],
        peak_input_output=[3,9],cache_input=.3,offpeak_half=True))
    (c.OUT/'live').mkdir();c.write_json(c.OUT/'live/ledger.json',dict(cap_cny=80,used_or_reserved_cny=0.,exhausted_accounts=[],phases={},provider='siliconflow',pool_exhaustion_notified=False))

def forecast(jobs,ledger):
    cal=c.read(c.ROOT/'outputs/016_disagreement_triggered_review_validation/token_calibration_001.json')['models']['v4_first']
    phase=ledger['phases'].get('headroom',{}).get('jobs',{})
    pending=[j for j in jobs if phase.get(j['request_id'],{}).get('status')!='received']
    expected=sum((math.ceil(sum(len(m['content']) for m in j['body']['messages'])*cal['input_factor']+200)*3+cal['output_allowance']*9)/1e6 for j in pending)
    reserve=c.read(c.OUT/'preparation_001/summary.json')['confirmation_planning_allowance_cny']
    projected=ledger['used_or_reserved_cny']+expected+reserve+5
    out=c.OUT/'budget_checks';out.mkdir(exist_ok=True)
    record=dict(created_utc=c.now(),used_or_reserved_cny=ledger['used_or_reserved_cny'],remaining_requests=len(pending),remaining_expected_cny=expected,
        conditional_confirmation_allowance_cny=reserve,failure_margin_cny=5,whole_task_projected_cny=projected,cap_cny=80,within_cap=projected<=80)
    c.write_json(out/f'estimate_{len(list(out.glob("*.json")))+1:03d}.json',record)
    c.require(record['within_cap'],'Whole017 forecast exceeds80; stop and report')
    print(c.canonical(record),flush=True)

def run(limit=64,workers=8):
    c.require(1<=limit<=64 and 1<=workers<=8,'Bounded batches only')
    c.require(not (c.OUT/'analysis_001').exists(),'Analysis started; sends closed')
    auth=c.read(c.OUT/'authority_001.json');c.old.check_hashes(auth['execution_sha256'])
    c.require(auth['protocol_sha256']==c.file_hash(c.OUT/'protocol_001.md') and auth['execution_policy_sha256']==c.file_hash(c.OUT/'execution_policy_001.json'),'Protocol changed')
    c.check(c.OUT/'preparation_001');jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl')
    # Case bundles minimize provider crossing; inside a case retain hashed condition/round order.
    jobs.sort(key=lambda j:(c.rank_id(j['proposition_id']),c.old.hash_rank(j['request_id'],'017/send/v1:')))
    ledgerpath=c.OUT/'live/ledger.json';ledger=c.read(ledgerpath)
    c.require(not ledger.get('bound_violation'),'Unexpected charge bound violation')
    forecast(jobs,ledger)
    state=ledger['phases'].setdefault('headroom',dict(jobs={j['request_id']:dict(status='pending',attempts=0,receipts=[]) for j in jobs}))
    c.require(not any(p['status']=='in_flight' for p in state['jobs'].values()),'Interrupted sends require receipt reconciliation; no blind resend')
    accounts=[a for a in c.old.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    c.require(accounts and accounts[0].alias=='account_2','Expected active pool starts at2')
    cfg=replace(load_config(c.ROOT/'.env.aliyun'),model=ALI_MODEL);ali=AliyunClient(cfg);sf=c.old.NATIVE.HttpClient()
    c.require(cfg.endpoint==auth.get('Alibaba_endpoint',cfg.endpoint),'Alibaba endpoint changed')
    if GLOBAL_ROUTE.exists() and c.read(GLOBAL_ROUTE).get('provider')=='aliyun':ledger['provider']='aliyun'
    lock=c.OUT/'task_api.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        folder=c.OUT/'live/headroom';folder.mkdir(exist_ok=True);sent=0;halt=False;last=time.monotonic()
        def perform(job,provider,account,attempt):
            body=dict(job['body']);body['model']=ALI_MODEL if provider=='aliyun' else c.MODEL
            actual=dict(job,body=body);start=c.now()
            try:tr=ali.send(body) if provider=='aliyun' else sf.send(account,actual)
            except Exception:tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=start,ended_utc=c.now())
            encoded=c.canonical(tr)
            for key in [cfg.api_key]+[a.key for a in accounts]:
                if key:encoded=encoded.replace(json.dumps(key,ensure_ascii=False)[1:-1],'[REDACTED_API_KEY]')
            return dict(request_id=job['request_id'],original_job_sha256=c.fingerprint(job),actual_body=body,actual_body_sha256=c.fingerprint(body),attempt=attempt,
                provider=provider,account='aliyun_main' if provider=='aliyun' else account.alias,endpoint=cfg.endpoint if provider=='aliyun' else c.old.NATIVE.ENDPOINTS['chat'],transport=json.loads(encoded))
        c.save(ledgerpath,ledger)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={}
            while True:
                account=next((a for a in accounts if a.alias not in ledger['exhausted_accounts']),None)
                if ledger['provider']=='siliconflow' and account is None:
                    # Wait for all old-provider requests to drain before routing the next batch.
                    halt=True
                    if not futures:
                        event=dict(created_utc=c.now(),provider='aliyun',reason='All enabled SiliconFlow accounts returned explicit unanswered balance errors',
                            exhausted_accounts=sorted(set(ledger['exhausted_accounts'])),source_task='017',notification_required=True)
                        GLOBAL_ROUTE.parent.mkdir(parents=True,exist_ok=True);c.save(GLOBAL_ROUTE,event)
                        c.write_json(c.OUT/'pool_exhausted_001.json',event);ledger['provider']='aliyun';c.save(ledgerpath,ledger)
                        print('SILICONFLOW_POOL_EXHAUSTED: notify user; subsequent batch uses registered Alibaba V4 snapshot',flush=True)
                if not halt:
                    for i,j in enumerate(jobs):
                        p=state['jobs'][j['request_id']]
                        if len(futures)>=workers or sent>=limit:break
                        if p['status'] not in ('pending','retry') or p['attempts']>=5:continue
                        if ledger['used_or_reserved_cny']+bound(j)>80:halt=True;break
                        ledger['used_or_reserved_cny']+=bound(j);p.update(status='in_flight',attempts=p['attempts']+1,started_utc=c.now())
                        c.save(ledgerpath,ledger);futures[pool.submit(perform,j,ledger['provider'],account,p['attempts'])]=(i,j);sent+=1
                if not futures:break
                done,_=wait(futures,timeout=1,return_when=FIRST_COMPLETED)
                for f in done:
                    i,j=futures.pop(f);r=f.result();p=state['jobs'][j['request_id']];tr=r['transport'];actual=dict(j,body=r['actual_body']);fee,basis=cost(actual,tr)
                    file=folder/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json';c.write_json(file,r)
                    p['receipts'].append(dict(file=file.name,sha256=c.file_hash(file),charge_cny=fee,charge_basis=basis))
                    ledger['used_or_reserved_cny']+=fee-bound(j)
                    if tr['http_status']==200:
                        p['status']='received';n=c.old.old14.normalize(actual,r,model=r['actual_body']['model'])
                        if n['status']!='success':halt=True
                    elif r['provider']=='siliconflow' and c.old.balance_exhausted(tr):
                        p['status']='retry';ledger['exhausted_accounts'].append(r['account'])
                    else:p['status']='retry' if p['attempts']<2 else 'failed';halt=True
                    if fee>bound(j)+1e-10:ledger['bound_violation']=True;halt=True
                    c.save(ledgerpath,ledger)
                if time.monotonic()-last>=30:
                    print('headroom received',sum(p['status']=='received' for p in state['jobs'].values()),'/',len(jobs),'budget',round(ledger['used_or_reserved_cny'],4),flush=True);last=time.monotonic()
        result=dict(sent=sent,received=sum(p['status']=='received' for p in state['jobs'].values()),total=len(jobs),used_cny=ledger['used_or_reserved_cny'],halt=halt,provider=ledger['provider'])
        print(c.canonical(result),flush=True);return result
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('authorize','run'));p.add_argument('--limit',type=int,default=64);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    authorize() if a.action=='authorize' else run(a.limit,a.workers)
