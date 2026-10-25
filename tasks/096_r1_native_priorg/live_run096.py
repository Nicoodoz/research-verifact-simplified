"""Authorized loopback R1 runner: bounded async workers, append-only receipts.
No GT or accuracy access. Latest live protocol supersedes offline runtime gates.
"""
import asyncio,sys,json,time,os,urllib.request,urllib.error,re,statistics,collections,argparse,datetime
import common096 as c
sys.path.insert(0,str(c.ROOT/'tasks/085_r1_70b_model_swap'))
from parse_r1 import ParserProfile,parse
O=c.OUT/'live_v1';P=c.PRIVATE/'live_v1';BASE='http://127.0.0.1:18000/v1'
RETRY={0,408,429,500,502,503,504}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):raise ValueError('Redirect forbidden')
def request(path,body=None):
    url=BASE+path if not path.startswith('@') else BASE[:-3]+path[1:]
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());start=c.now();t=time.monotonic()
    rq=urllib.request.Request(url,data=c.encoded(body) if body else None,headers={'Authorization':'Bearer EMPTY','Content-Type':'application/json'})
    try:
        with op.open(rq,timeout=900 if body else 20) as res:raw=res.read();status=res.status
        err=None
    except urllib.error.HTTPError as e:raw=e.read();status=e.code;err='HTTPError'
    except (OSError,ValueError) as e:raw=b'';status=0;err=type(e).__name__
    return raw,dict(http_status=status,error_type=err,outcome_unknown=status==0 and body is not None,started_utc=start,ended_utc=c.now(),elapsed_seconds=time.monotonic()-t)
def durable(p,raw):
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def probe(path):
    raw,rec=request(path);d=P/'probes'/str(time.time_ns());d.mkdir(parents=True);durable(d/'response.raw',raw);c.put(d/'receipt.json',dict(rec,path=path,response_sha256=c.sha(d/'response.raw')))
    return raw,rec
def health():
    raw,r=probe('/models');assert r['http_status']==200,'R1_ENDPOINT_UNREACHABLE'
    cards=json.loads(raw)['data'];assert len(cards)==1 and cards[0]['id']==c.MODEL and cards[0].get('max_model_len')==20000,'MODEL_IDENTITY_MISMATCH'
    met,mr=probe('@/metrics');text=met.decode(errors='replace') if mr['http_status']==200 else ''
    up=re.findall(r'^process_start_time_seconds\s+(\S+)',text,re.M)
    out=dict(utc=c.now(),models_http=200,model=cards[0]['id'],root=cards[0]['root'],max_model_len=20000,models_sha256=c.key('',raw.decode()),metrics_http=mr['http_status'],process_start_time=up,OOM='not observable via available endpoint',restart='unknown unless process_start_time exposed')
    c.append(O/'service_health.jsonl',out);return out
def idle():
    for _ in range(2):
        raw,rec=probe('@/metrics')
        if rec['http_status']!=200:return False
        txt=raw.decode(errors='replace')
        for name in ['num_requests_running','num_requests_waiting']:
            vals=re.findall(r'^vllm:'+name+r'(?:\{[^\n]*\})?\s+([0-9.eE+-]+)\s*$',txt,re.M)
            if not vals or any(float(v)!=0 for v in vals):return False
        time.sleep(2)
    c.append(O/'runtime_ledger.jsonl',dict(event='unknown_inflight_idle_verified',utc=c.now()));return True
def attempts(j):
    out=[]
    for f in sorted((P/'attempts'/j['request_id']).glob('*/request.json'),key=lambda p:int(p.parent.name)):
        assert c.read(f)['body_sha256']==j['body_sha256'];rp=f.parent/'receipt.json'
        r=c.read(rp) if rp.exists() else dict(http_status=None,outcome_unknown=True)
        if r.get('response_sha256'):assert c.sha(f.parent/'response.raw')==r['response_sha256'] and c.sha(f)==r['request_sha256']
        out.append((f.parent,r))
    assert sum(r.get('http_status')==200 for _,r in out)<=1;return out
def success(j):return next((p for p,r in attempts(j) if r.get('http_status')==200),None)
def invoke(j,stage):
    existing=success(j)
    if existing:return existing,200
    hist=attempts(j);n=len(hist)+1;assert n<=3,'RETRY_LIMIT'
    d=P/'attempts'/j['request_id']/str(n);d.mkdir(parents=True,exist_ok=False)
    c.put(d/'request.json',dict(request_id=j['request_id'],body_sha256=j['body_sha256'],body=j['body'],id=j['id'],stage=stage,attempt=n,utc=c.now()))
    raw,rec=request('/chat/completions',j['body']);durable(d/'response.raw',raw)
    c.put(d/'receipt.json',dict(rec,request_sha256=c.sha(d/'request.json'),response_sha256=c.sha(d/'response.raw')))
    c.append(P/'request_ledger.jsonl',dict(request_id=j['request_id'],id=j['id'],stage=stage,attempt=n,**rec))
    if rec['http_status']==200:
        try:response=json.loads(raw)
        except ValueError:response={}
        if response.get('model')!=c.MODEL:raise RuntimeError('HTTP200_MODEL_MISMATCH_RETAINED')
    return d,rec['http_status']
def jobs():
    f=c.read(O/'freeze.json');assert c.sha(P/'jobs.jsonl')==f['jobs_sha256']
    jj=c.lines(P/'jobs.jsonl')
    for j in jj:
        b=j['body'];assert c.digest(b)==j['body_sha256'] and b['model']==c.MODEL and b['max_tokens']==8192 and b['temperature']==0 and b['top_p']==1
        assert set(json.loads(b['messages'][1]['content']))=={'proposition','reference'}
    return jj
def profile():return ParserProfile.from_json(c.read(O/'parser_profile.json'))
def parsed(j):
    d=success(j);return parse((d/'response.raw').read_bytes(),profile()) if d else None
def pct(v,q):
    v=sorted(v);return v[min(len(v)-1,max(0,__import__('math').ceil(q*len(v))-1))] if v else None
def metrics(jj,wall):
    pp=[parsed(j) for j in jj if success(j)];rr=[c.read(success(j)/'receipt.json') for j in jj if success(j)];lat=[r['elapsed_seconds'] for r in rr];comp=[(p.get('usage') or {}).get('completion_tokens',0) for p in pp];prompt=sum((p.get('usage') or {}).get('prompt_tokens',0) for p in pp);hist=[r for j in jj for _,r in attempts(j)]
    return dict(requests=len(jj),success=len(pp),failure=len(jj)-len(pp),attempts=len(hist),raw_valid=sum(p['valid'] for p in pp),core_valid=sum(p['valid'] and p['label_scores'] is not None for p in pp),wall_seconds=wall,requests_per_min=len(pp)/wall*60 if wall else None,prompt_tokens=prompt,completion_tokens=sum(comp),completion_tokens_per_second=sum(comp)/wall if wall else None,total_tokens_per_second=(prompt+sum(comp))/wall if wall else None,latency_median=statistics.median(lat) if lat else None,latency_p90=pct(lat,.9),latency_max=max(lat,default=None),completion_median=statistics.median(comp) if comp else None,completion_p90=pct(comp,.9),completion_max=max(comp,default=None),finish_reasons=dict(collections.Counter(p['finish'] for p in pp)),http_statuses=dict(collections.Counter(str(r.get('http_status')) for r in hist)),timeout_or_unknown=sum(r.get('http_status')==0 for r in hist))
async def run_stage(jj,cc,name):
    record=O/f'stage_{name}.json'
    if record.exists():return c.read(record)
    before=await asyncio.to_thread(health);started=c.now();t=time.monotonic();pending=[j for j in jj if not success(j)]
    if any(attempts(j) and attempts(j)[-1][1].get('outcome_unknown') for j in pending):
        assert await asyncio.to_thread(idle),'UNRESOLVED_INFLIGHT_NO_RETRY'
    total_done=sum(success(j) is not None for j in jj);stop=asyncio.Event()
    async def pass_jobs(todo):
        nonlocal total_done
        queue=asyncio.Queue()
        for j in todo:queue.put_nowait(j)
        failed=[];errors=[]
        async def worker():
            nonlocal total_done
            while not stop.is_set():
                try:j=queue.get_nowait()
                except asyncio.QueueEmpty:return
                try:
                    if (O/'tier_selection.json').exists():
                        ts=c.read(O/'tier_selection.json')
                        if time.time()>ts['formal_deadline_epoch']:raise RuntimeError('AUTHORIZED_TIME_LIMIT_STOP_NEW_SENDS')
                    d,status=await asyncio.to_thread(invoke,j,name)
                    if status!=200:failed.append((j,status));stop.set()
                    else:
                        total_done+=1
                        if total_done%25==0 or total_done==len(jj):
                            elapsed=time.monotonic()-t;rate=total_done/max(elapsed,1)*60
                            progress=dict(stage=name,completed=total_done,N=len(jj),remaining=len(jj)-total_done,requests_per_min=rate,eta_minutes=(len(jj)-total_done)/rate,utc=c.now())
                            c.append(O/'progress.jsonl',progress);print(json.dumps(progress),flush=True)
                            await asyncio.to_thread(health)
                except Exception as e:errors.append(e);stop.set()
                finally:queue.task_done()
        await asyncio.gather(*(worker() for _ in range(cc)))
        if errors:raise errors[0]
        return failed
    while pending:
        stop.clear();failed=await pass_jobs(pending)
        if not failed:break
        assert all(s in RETRY for _,s in failed),'PERSISTENT_NONRETRYABLE_HTTP'
        assert all(len(attempts(j))<3 for j,_ in failed),'FINITE_RECOVERY_EXHAUSTED'
        if any(s==0 for _,s in failed):assert await asyncio.to_thread(idle),'UNRESOLVED_INFLIGHT_NO_RETRY'
        await asyncio.sleep(3);pending=[j for j in jj if not success(j)]
    after=await asyncio.to_thread(health);wall=time.monotonic()-t
    if name=='P0':
        j=jj[0];d=success(j);obj=c.read(d/'response.raw');msg=obj['choices'][0]['message']
        assert isinstance(msg.get('reasoning_content'),str) and isinstance(msg.get('content'),str) and msg['content'].strip(),'P0_PROTOCOL_CONTENT_FAILURE'
        p=dict(status='FROZEN_AFTER_AB_NO_GT',content_path=['choices',0,'message','content'],reasoning_path=['choices',0,'message','reasoning_content'],finish_path=['choices',0,'finish_reason'],usage_path=['usage'],source_request_id=j['request_id'],parser_source_sha256=c.sha(c.ROOT/'tasks/085_r1_70b_model_swap/parse_r1.py'),evaluation_GT_read=False)
        c.put(O/'parser_profile.json',p)
        pp=parsed(j);assert pp['valid'] and pp['label_scores'] is not None and not pp['truncated'] and pp['usage'],'P0_PARSE_FAILURE'
        local=next(r['input_tokens'] for r in c.lines(O/'local_token_lengths.jsonl') if r['id']==j['id']);assert pp['usage']['prompt_tokens']==local and local+8192<=20000,'P0_CONTEXT_OR_TOKENIZER_MISMATCH'
    m=metrics(jj,wall);m.update(stage=name,concurrency=cc,started_utc=started,ended_utc=c.now(),health_before=before,health_after=after)
    m['stable']=m['success']==len(jj) and m['core_valid']==len(jj) and m['finish_reasons'].get('length',0)==0 and m['latency_p90']<600 and (not before['process_start_time'] or before['process_start_time']==after['process_start_time'])
    c.put(record,m);c.append(O/'runtime_ledger.jsonl',m);print('STAGE_COMPLETE',name,json.dumps({k:m[k] for k in ['success','core_valid','wall_seconds','requests_per_min','stable']}),flush=True);return m
async def benchmark():
    jj=jobs();idx={j['id']:j for j in jj};plan=c.read(O/'benchmark_plan.json');results=[]
    for name in ['P0','P1','P2','P3','P4','P5']:
        if name=='P5' and results[-1]['requests_per_min']<1.1*results[-2]['requests_per_min']:break
        cfg=plan[name];m=await run_stage([idx[i] for i in cfg['ids']],cfg['concurrency'],name);results.append(m)
        if not m['stable']:raise RuntimeError('PREFLIGHT_OR_BENCHMARK_UNSTABLE_NO_FORMAL')
        if len(results)>2 and m['latency_p90']>3*results[-2]['latency_p90']:raise RuntimeError('LATENCY_UNCONTROLLED_NO_FORMAL')
    chosen=results[1]
    for m in results[2:]:
        if m['requests_per_min']>=chosen['requests_per_min']*(1.1 if m['concurrency']>=12 else 1.0):chosen=m
    done={j['id'] for j in jj if success(j)};forecasts={};tiers={'A':(800,200),'B':(600,120),'C':(400,100)}
    # A fixed25% throughput allowance protects against longer calibration/output.
    for tier,(n,d) in tiers.items():
        ids={j['id'] for j in jj if j['stage']=='calibration'}|{r['id'] for r in c.lines(O/f'natural{n}.jsonl')}|{r['id'] for r in c.lines(O/f'diagnostic{d}.jsonl')}
        forecasts[tier]=dict(total=len(ids),completed=len(ids&done),remaining=len(ids-done),predicted_hours=len(ids-done)/chosen['requests_per_min']/60*1.25)
    tier='A' if forecasts['A']['predicted_hours']<=3.5 else 'B' if forecasts['B']['predicted_hours']<=3.5 else 'C'
    c.put(O/'concurrency_benchmark.json',dict(stages=results,selected_concurrency=chosen['concurrency'],selected_rate=chosen['requests_per_min'],throughput_allowance=1.25,forecasts=forecasts,completed=len(done),evaluation_accuracy_read=False))
    if forecasts['C']['predicted_hours']>4:raise RuntimeError('R1_RUNTIME_TOO_HIGH')
    n,d=tiers[tier];ids=[j['id'] for j in jj if j['stage']=='calibration']+[r['id'] for r in c.lines(O/f'natural{n}.jsonl')]+[r['id'] for r in c.lines(O/f'diagnostic{d}.jsonl')]
    assert done<=set(ids)
    c.put(O/'tier_selection.json',dict(tier=tier,natural=n,diagnostic=d,calibration=143,ids=ids,ids_sha256=c.digest(ids),concurrency=chosen['concurrency'],forecasts=forecasts,selected_utc=c.now(),formal_deadline_epoch=time.time()+4*3600,selection_uses_accuracy=False))
    print('TIER_FROZEN',tier,'concurrency',chosen['concurrency'],'remaining_hours',forecasts[tier]['predicted_hours'],flush=True)
async def formal():
    sel=c.read(O/'tier_selection.json');ids=set(sel['ids']);jj=[j for j in jobs() if j['id'] in ids]
    for stage in ['calibration','natural','diagnostic']:await run_stage([j for j in jj if j['stage']==stage],sel['concurrency'],stage)
    reconciliation=[]
    for j in jj:
        d=success(j);assert d;pp=parsed(j);rec=c.read(d/'receipt.json')
        reconciliation.append(dict(id=j['id'],stage=j['stage'],request_id=j['request_id'],body_sha256=j['body_sha256'],response_sha256=rec['response_sha256'],receipt_sha256=c.sha(d/'receipt.json'),http_status=200,raw_valid=pp['valid'],core_valid=pp['valid'] and pp['label_scores'] is not None,finish=pp['finish'],usage=pp['usage'],attempts=len(attempts(j))))
    c.putl(O/'response_reconciliation.jsonl',reconciliation)
    hist=[r for j in jj for _,r in attempts(j)];start=min(r['started_utc'] for r in hist);end=max(r['ended_utc'] for r in hist);wall=(datetime.datetime.fromisoformat(end)-datetime.datetime.fromisoformat(start)).total_seconds()
    result=dict(status='R1_INFERENCE_DONE',utc=c.now(),counts=dict(collections.Counter(j['stage'] for j in jj)),HTTP200=len(jj),core_valid=sum(r['core_valid'] for r in reconciliation),wall_seconds=wall,concurrency=sel['concurrency'],requests_per_min=len(jj)/wall*60,prompt_tokens=sum((r['usage'] or {}).get('prompt_tokens',0) for r in reconciliation),completion_tokens=sum((r['usage'] or {}).get('completion_tokens',0) for r in reconciliation),response_directory=str(P/'attempts'),reconciliation=str(O/'response_reconciliation.jsonl'),reconciliation_sha256=c.sha(O/'response_reconciliation.jsonl'),GPU_hourly_price=None,GPU_rent=None,cloud_API_cost=0)
    c.put(O/'R1_INFERENCE_DONE.json',result);print('R1_INFERENCE_DONE',json.dumps(result,ensure_ascii=False),flush=True);print('现在可以关闭AutoDL实例，后续PriorG拟合、统计和报告全部离线完成。',flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['probe','benchmark','formal','all','status']);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    if a.command=='status':print('HTTP200',sum(success(j) is not None for j in jobs()));return
    if not a.execute:print('DRY_RUN_NO_NETWORK',a.command);return
    lock=P/'run.lock';lock.parent.mkdir(parents=True,exist_ok=True);fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        if a.command=='probe':print(json.dumps(health()));return
        if a.command in ['benchmark','all']:asyncio.run(benchmark())
        if a.command in ['formal','all']:asyncio.run(formal())
    except BaseException as e:
        c.append(O/'execution_events.jsonl',dict(utc=c.now(),event='stopped',error=str(e),type=type(e).__name__));raise
    finally:lock.unlink(missing_ok=True)
if __name__=='__main__':main()
