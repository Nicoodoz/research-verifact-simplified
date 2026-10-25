"""Durable bounded 020 execution; preserves every answer and never retries HTTP200."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import replace
from decimal import Decimal
import argparse, json, os, time
import common020 as c
from atomic020 import save as save_ledger, load as load_ledger
TRANSIENT = {408,429,500,502,503,504}

def route_account(accounts, exhausted):
    return next((a for a in accounts if a.alias not in exhausted),None)

def allowed_budget(used, reserve, cap=80):
    return Decimal(str(used))+Decimal(str(reserve)) <= Decimal(str(cap))

def _sf_json_decode_error(tr):
    try:
        body=json.loads(tr.get('body_text',''))
        return body.get('code')==20015 and body.get('message')=='JSON decode error'
    except (ValueError,TypeError,AttributeError):
        return False

def run(stage, limit=100000, workers=16):
    c.require(stage in c.PHASES and 1<=workers<=16 and limit>0,'Invalid execution range')
    c.require(not (c.OUT/stage/'analysis_001').exists(),'Analysis exists; stage sends closed')
    auth=c.check_manifest(c.OUT/'authority.json')
    c.check_manifest(c.job_preparation(stage)/'manifest.json')
    jobs=c.jsonlines(c.job_preparation(stage)/'jobs.jsonl')
    accounts=[a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    c.require([a.alias for a in accounts]==auth['accounts'],'Pool configuration changed')
    cfg=replace(c.load_config(c.ROOT/'.env.aliyun'),model=c.ALI_MODEL)
    c.require(cfg.endpoint==auth['Alibaba_endpoint'],'Alibaba endpoint changed')
    sf=c.NATIVE.HttpClient(); ali=c.AliyunClient(cfg,timeout=120)
    folder=c.OUT/stage/'live'; folder.mkdir(parents=True,exist_ok=True)
    lp=c.OUT/'live_ledger.json'; lock=c.OUT/'task_api.lock'
    with lock.open('x',encoding='utf-8') as f: f.write(str(os.getpid()))
    try:
        state=load_ledger(lp) if (lp.exists() or lp.with_name(lp.stem+'_shadow'+lp.suffix).exists()) else dict(cap_cny=80,used_or_reserved_cny=0.,provider='siliconflow',exhausted_accounts=[],phases={})
        if c.GLOBAL_ROUTE.exists() and c.read(c.GLOBAL_ROUTE).get('provider')=='aliyun': state['provider']='aliyun'
        phase=state['phases'].setdefault(stage,dict(jobs={j['request_id']:dict(status='pending',attempts=0,transient=0,unknown=0,receipts=[]) for j in jobs}))
        c.require(set(phase['jobs'])=={j['request_id'] for j in jobs},'Job set changed')
        def checkpoint():
            state['_checkpoint_seq']=int(state.get('_checkpoint_seq',0))+1
            save_ledger(lp,state)
        def actual(job,provider):
            b=dict(job['body'])
            if job['kind']=='chat': b['model']=c.ALI_MODEL if provider=='aliyun' else c.MODEL
            return b
        def receipt_path(i,attempt): return folder/f'receipt_{i+1:06d}_{attempt:02d}.json'
        def finish(i,j,r):
            p=phase['jobs'][j['request_id']]; tr=r['transport']
            c.require(r['request_id']==j['request_id'] and r['attempt']==p['attempts'] and r['job_sha256']==c.fingerprint(j),'Receipt binding mismatch')
            fee,basis=c.charge(dict(j,body=r['actual_body']),tr)
            state['used_or_reserved_cny']=float(Decimal(str(state['used_or_reserved_cny']))-Decimal(str(p['reserved_cny']))+Decimal(str(fee)))
            ptr=dict(file=receipt_path(i,p['attempts']).relative_to(c.OUT).as_posix(),sha256=c.file_hash(receipt_path(i,p['attempts'])),charge_cny=fee,charge_basis=basis)
            p['receipts'].append(ptr)
            if tr['http_status']==200:
                p['status']='received'
                parsed=c.parse(dict(j,body=r['actual_body']),tr); p['parse_status']=parsed['status']; p['parse_errors']=parsed['errors']
                state['consecutive_transport_errors']=0
                if 'unexpected_thinking' in parsed['errors']: state['pause_reason']='unexpected_thinking'
            elif r['provider']=='siliconflow' and c.balance_exhausted(tr):
                if r['account'] not in state['exhausted_accounts']: state['exhausted_accounts'].append(r['account'])
                p['status']='pending'
            elif tr.get('outcome_unknown'):
                p['unknown']+=1; p['status']='retry' if p['unknown']<2 else 'failed_unknown'
                p['retry_after']=time.time()+20
                state['consecutive_transport_errors']=state.get('consecutive_transport_errors',0)+1
            elif r['provider']=='siliconflow' and tr['http_status']==400 and _sf_json_decode_error(tr):
                p['transient']+=1; p['status']='retry' if p['transient']<3 else 'failed_service'
                p['retry_after']=time.time()+20
                state['consecutive_transport_errors']=state.get('consecutive_transport_errors',0)+1
                state.setdefault('provider_json_decode_retries',[]).append(dict(created_utc=c.now(),request_id=j['request_id'],attempt=p['attempts']))
            elif tr['http_status'] in TRANSIENT:
                p['transient']+=1; p['status']='retry' if p['transient']<3 else 'failed_service'
                p['retry_after']=time.time()+20
                if tr['http_status']==429:
                    state['next_send_at']=max(state.get('next_send_at',0),time.time()+70)
                    state['pace_multiplier']=min(4.,state.get('pace_multiplier',1.)*1.5)
                    state.setdefault('rate_limit_adjustments',[]).append(dict(created_utc=c.now(),next_send_at=state['next_send_at'],pace_multiplier=state['pace_multiplier']))
                state['consecutive_transport_errors']=state.get('consecutive_transport_errors',0)+1
            else:
                p['status']='failed_configuration'; state['pause_reason']='configuration_http_'+str(tr['http_status'])
            if p['attempts']>=12 and p['status'] in ('pending','retry'): p['status']='failed_attempt_limit'
            if fee>p['reserved_cny']+1e-10: state['pause_reason']='cost_bound_violation'
            if state.get('consecutive_transport_errors',0)>=5: state['pause_reason']='transport_circuit_breaker'
            checkpoint()
        for i,j in enumerate(jobs):
            p=phase['jobs'][j['request_id']]
            for ptr in p['receipts']: c.require(c.file_hash(c.OUT/ptr['file'])==ptr['sha256'],'Saved receipt changed')
            if p['status']=='in_flight':
                rp=receipt_path(i,p['attempts'])
                if rp.exists(): finish(i,j,c.read(rp))
                else:
                    p.setdefault('unreceipted_attempts',[]).append(dict(attempt=p['attempts'],reserved_cny=p['reserved_cny']))
                    p['unknown']+=1; p['status']='retry' if p['unknown']<2 else 'failed_unknown'; p['retry_after']=time.time()+20
        checkpoint()
        c.require(not state.get('pause_reason'),'Resolve recorded pause before resuming: '+str(state.get('pause_reason')))
        secrets=[cfg.api_key]+[a.key for a in accounts]
        def perform(i,j,provider,account,attempt):
            b=actual(j,provider); start=c.now()
            try: tr=ali.send(b) if provider=='aliyun' else sf.send(account,dict(j,body=b))
            except Exception: tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=start,ended_utc=c.now())
            encoded=c.canonical(tr)
            for key in secrets:
                if key: encoded=encoded.replace(json.dumps(key,ensure_ascii=False)[1:-1],'[REDACTED_API_KEY]')
            return dict(request_id=j['request_id'],job_sha256=c.fingerprint(j),actual_body=b,actual_body_sha256=c.fingerprint(b),
                attempt=attempt,provider=provider,account='aliyun_main' if provider=='aliyun' else account.alias,
                endpoint=cfg.endpoint if provider=='aliyun' else c.NATIVE.ENDPOINTS[j['kind']],transport=json.loads(encoded))
        sent=0; last=time.monotonic(); halt=None
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={}
            while True:
                account=route_account(accounts,state['exhausted_accounts'])
                if (c.OUT/'STOP_REQUESTED').exists(): halt='stop_requested'
                if state.get('pause_reason'): halt=state['pause_reason']
                if state['provider']=='siliconflow' and account is None: halt='pool_exhausted'
                if state['provider']=='aliyun' and any(j['kind']!='chat' for j in jobs): halt='Alibaba_same_BGE_service_not_registered'
                if not halt and sent<limit and time.time() >= state.get('next_send_at',0):
                    for i,j in enumerate(jobs):
                        p=phase['jobs'][j['request_id']]
                        if len(futures)>=workers or sent>=limit: break
                        if p['status'] not in ('pending','retry') or p.get('retry_after',0)>time.time(): continue
                        reserve=c.bound(dict(j,body=actual(j,state['provider'])))
                        if not allowed_budget(state['used_or_reserved_cny'],reserve): halt='budget_limit'; break
                        state['used_or_reserved_cny']=float(Decimal(str(state['used_or_reserved_cny']))+Decimal(str(reserve)))
                        p.update(status='in_flight',attempts=p['attempts']+1,reserved_cny=reserve,started_utc=c.now())
                        pace=(2.5 if j['kind']=='chat' else 0.6)*state.get('pace_multiplier',1.)
                        state['next_send_at']=time.time()+pace
                        checkpoint(); futures[pool.submit(perform,i,j,state['provider'],account,p['attempts'])]=(i,j); sent+=1
                        break  # Uniform token-aware pacing, not a concurrency burst.
                if not futures:
                    if halt=='pool_exhausted':
                        event=dict(provider='aliyun',created_utc=c.now(),source_task='020',exhausted_accounts=state['exhausted_accounts'],
                            reason='all_enabled_accounts_explicit_unanswered_balance_error',notification_required=True)
                        c.GLOBAL_ROUTE.parent.mkdir(parents=True,exist_ok=True); c.save(c.GLOBAL_ROUTE,event)
                        state['provider']='aliyun'; checkpoint()
                        print('SILICONFLOW_POOL_EXHAUSTED: notify user; subsequent run uses Alibaba single key',flush=True)
                    if not halt and sent<limit and any(p['status'] in ('pending','retry') for p in phase['jobs'].values()): time.sleep(0.5); continue
                    break
                done,_=wait(futures,timeout=0.2,return_when=FIRST_COMPLETED)
                for f in done:
                    i,j=futures.pop(f); r=f.result(); c.write_json(receipt_path(i,r['attempt']),r); finish(i,j,r)
                if time.monotonic()-last>=20:
                    counts={s:sum(p['status']==s for p in phase['jobs'].values()) for s in {p['status'] for p in phase['jobs'].values()}}
                    print(c.canonical(dict(stage=stage,counts=counts,total=len(jobs),used_or_reserved_cny=round(state['used_or_reserved_cny'],6),provider=state['provider'],sent=sent)),flush=True); last=time.monotonic()
        counts={s:sum(p['status']==s for p in phase['jobs'].values()) for s in {p['status'] for p in phase['jobs'].values()}}
        result=dict(stage=stage,created_utc=c.now(),counts=counts,total=len(jobs),sent=sent,halt=halt,provider=state['provider'],used_or_reserved_cny=state['used_or_reserved_cny'],complete=counts.get('received',0)==len(jobs))
        c.save(folder/'status.json',result); print(c.canonical(result),flush=True)
        sealpath=c.OUT/stage/'receipt_manifest.json'
        if result['complete'] and not sealpath.exists():
            c.write_json(sealpath,dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in folder.glob('receipt_*.json')}))
        return result
    finally: lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=list(c.PHASES));p.add_argument('--limit',type=int,default=100000);p.add_argument('--workers',type=int,default=16);a=p.parse_args()
    run(a.stage,a.limit,a.workers)
