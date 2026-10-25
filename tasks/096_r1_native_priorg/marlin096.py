"""User-authorized AWQ -> AWQ-Marlin transition; frozen samples unchanged."""
import sys,os,time,json,asyncio,copy,argparse,signal
import common096 as c
import live_run096 as r
OLD_O=c.OUT/'live_v1';OLD_P=c.PRIVATE/'live_v1'
BACKEND='valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k'
O=c.OUT/BACKEND;P=c.PRIVATE/BACKEND
_original_parsed=r.parsed
_original_metrics=r.metrics
def parsed(j):
    result=_original_parsed(j)
    if result is not None:
        #085 clinical parser deliberately stays unchanged. Read envelope metadata
        #even when content=None caused it to exit before usage/finish assignment.
        env=c.read(r.success(j)/'response.raw')
        if result.get('usage') is None:result['usage']=env.get('usage')
        if result.get('finish') is None:result['finish']=(env.get('choices') or [{}])[0].get('finish_reason')
    return result
def metrics(jj,wall):
    value=_original_metrics(jj,wall)
    value['finish_reasons']={str(k) if k is not None else 'null':v for k,v in value['finish_reasons'].items()}
    return value
def atomic_put(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert c.read(path)==obj;return
    tmp=path.with_name(path.name+'.pending')
    with tmp.open('xb') as f:f.write(c.encoded(obj)+b'\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def invoke(j,stage):
    if (P/'STOP_REQUESTED').exists():raise RuntimeError('USER_INTERRUPT_DRAINED_NO_NEW_SENDS')
    existing=r.success(j)
    if existing:return existing,200
    hist=r.attempts(j);n=len(hist)+1;assert n<=3
    d=P/'attempts'/j['request_id']/str(n);d.mkdir(parents=True,exist_ok=False)
    atomic_put(d/'request.json',dict(request_id=j['request_id'],backend_id=BACKEND,body_sha256=j['body_sha256'],body=j['body'],id=j['id'],stage=stage,attempt=n,utc=c.now()))
    raw,rec=r.request('/chat/completions',j['body']);r.durable(d/'response.raw',raw)
    atomic_put(d/'receipt.json',dict(rec,backend_id=BACKEND,request_sha256=c.sha(d/'request.json'),response_sha256=c.sha(d/'response.raw')))
    c.append(P/'request_ledger.jsonl',dict(request_id=j['request_id'],backend_id=BACKEND,id=j['id'],stage=stage,attempt=n,**rec))
    if rec['http_status']==200:
        try:response=json.loads(raw)
        except ValueError:response={}
        if response.get('model')!=c.MODEL:raise RuntimeError('HTTP200_MODEL_MISMATCH_RETAINED')
    return d,rec['http_status']
def activate():r.O=O;r.P=P;r.invoke=invoke;r.parsed=parsed;r.metrics=metrics
def prepare():
    O.mkdir(parents=True,exist_ok=True);P.mkdir(parents=True,exist_ok=True)
    inventory=[]
    for f in sorted((OLD_P/'attempts').glob('*/request.json')):raise AssertionError('Unexpected flat attempts')
    for f in sorted((OLD_P/'attempts').glob('*/*/request.json')):
        q=c.read(f);rp=f.parent/'receipt.json';rec=c.read(rp) if rp.exists() else None;response=f.parent/'response.raw'
        inventory.append(dict(request_id=q['request_id'],id=q['id'],stage=q['stage'],attempt=q['attempt'],http_status=rec.get('http_status') if rec else None,incomplete=rec is None,unknown_outcome=rec is None or rec.get('outcome_unknown',False),response_saved=response.exists(),request_sha256=c.sha(f),response_sha256=c.sha(response) if response.exists() else None,receipt_sha256=c.sha(rp) if rp.exists() else None,classification='AWQ_DIAGNOSTIC_ONLY',backend_uncertainty='Any late output after restart remains excluded; no formal reuse'))
    transition=dict(old_backend='awq',new_backend='awq_marlin',backend_id=BACKEND,reason='runtime-only performance diagnosis before formal evaluation',performance_GT_read_before_switch=False,sample_freeze_changed=False,utc=c.now(),old_runner_stopped_pid=30956,old_artifacts=inventory,old_P0_HTTP200=sum(x['stage']=='P0' and x['http_status']==200 for x in inventory),old_P1_HTTP200=sum(x['stage']=='P1' and x['http_status']==200 for x in inventory),incomplete_attempts=sum(x['incomplete'] for x in inventory),unknown_outcomes=sum(x['unknown_outcome'] for x in inventory),saved_responses=sum(x['response_saved'] for x in inventory),old_freeze_sha256=c.sha(OLD_O/'freeze.json'))
    c.put(O/'backend_transition.json',transition)
    c.write(O/'backend_transition.md',f'''# AWQ → AWQ-Marlin

仅因用户核实部署kernel速度异常而切换，未读取旧P0/P1准确率。旧runner后台PID30956已停止，旧锁和所有工件保留。

旧P0 HTTP200：{transition['old_P0_HTTP200']}；旧P1 HTTP200：{transition['old_P1_HTTP200']}；未完成attempt：{transition['incomplete_attempts']}；unknown：{transition['unknown_outcomes']}；已保存response：{transition['saved_responses']}。

旧AWQ所有输出均AWQ_DIAGNOSTIC_ONLY，不用于R1评价或拟合，不补跑旧unknown。新backend请求ID包含backend身份，同命题旧成功不阻止新backend首次调用；新backend内部HTTP200禁止重发。

样本、GT比例、校准监督、claim/C48和科学请求body不变。manifest的kernel由用户提供，/models只独立证明served model与context，不伪称远程权重/kernel逐字节验证。
''')
    oldfreeze=c.read(OLD_O/'freeze.json')
    for name,h in oldfreeze['files'].items():assert c.sha(OLD_O/name)==h
    jobs=c.lines(OLD_P/'jobs.jsonl')
    for j in jobs:
        oldid=j['request_id'];j['source_request_id']=oldid;j['backend_id']=BACKEND;j['request_id']=c.key(BACKEND+'/',oldid+'/'+j['body_sha256'])[:32]
        assert c.digest(j['body'])==j['body_sha256']
    c.putl(P/'jobs.jsonl',jobs)
    # Exact copies, not a new sampling operation. Original freeze remains unchanged.
    for name in oldfreeze['files']:
        if name=='request_manifest.jsonl':continue
        target=O/name
        if target.exists():assert target.read_bytes()==(OLD_O/name).read_bytes()
        else:target.write_bytes((OLD_O/name).read_bytes())
    c.putl(O/'request_manifest.jsonl',[{k:j[k] for k in ['id','sid','stage','request_id','body_sha256','backend_id','source_request_id']} for j in jobs])
    c.put(O/'freeze.json',dict(status='BACKEND_NAMESPACE_AMENDMENT_NO_SAMPLE_CHANGE',jobs_sha256=c.sha(P/'jobs.jsonl'),source_freeze_sha256=c.sha(OLD_O/'freeze.json'),backend_id=BACKEND,scientific_body_unchanged=True,sample_freeze_changed=False,files={name:c.sha(O/name) for name in oldfreeze['files']}))
    oldplan=c.read(OLD_O/'benchmark_plan.json');plan={}
    for label,source,n,cc in [('M0','P0',1,1),('M1','P1',4,2),('M2','P2',8,4),('M3','P3',12,8),('M4','P4',16,12)]:plan[label]=dict(ids=oldplan[source]['ids'][:n],concurrency=cc)
    c.put(O/'marlin_benchmark_plan.json',plan)
    c.put(O/'backend_manifest.json',dict(backend_id=BACKEND,created_utc=c.now(),served_model=c.MODEL,model_source='same ModelScope Valdemardi AWQ weights; user attestation',model_path='/root/autodl-tmp/models/models/Valdemardi--DeepSeek-R1-Distill-Llama-70B-AWQ/snapshots/master',immutable_revision=None,vllm='0.10.1.1',quantization='awq_marlin',dtype='float16',max_model_len=20000,reasoning_parser='deepseek_r1',temperature=0,top_p=1,max_tokens=8192,endpoint=r.BASE,changed_from_old='execution kernel awq -> awq_marlin only, user-reported',runtime_identity_provenance='kernel/vllm/GPU attested by user; model/context independently checked via endpoint',GPU='A80080GB PCIe',GPU_hourly_price=None,source_attachment_sha256=c.sha(c.Path('C:/Users/13359/.codex/attachments/dea802ac-e494-4a2d-9d84-e3071a5abd2b/已粘贴的文本.txt'))))
    c.write(O/'protocol_amendment.md','''# 新backend运行协议

继承live_v1/protocol.md的科学比较、监督、评价、隐私和不重发规则。旧AWQ诊断全部排除，正式请求只用本backend。

M0同旧P0命题，原body不变；reasoning必须非空，三分数有效，无截断。M0延迟>180秒即停止AWQ_MARLIN_SINGLE_TOO_SLOW。M1/M2/M3分别2并发4条、4并发8条、8并发12条；M3稳定且相对M2吞吐增益≥10%时测试M4=12并发16条。本次不做16并发（非必需）。8对4、12对8增益不足10%优先较低档。均来自原冻结不同Natural400 ID，正式可复用。

所有稳定性原指标保留，M0180秒用户门槛优先。按新实测吞吐加原冻结25%余量选A/B≤3.5小时、C≤4小时，否则R1_RUNTIME_TOO_HIGH。不得用旧AWQ速度或预测正确性选规模。sample freeze不变。

正式完成通知R1_INFERENCE_DONE后等待用户确认GPU关闭，再执行离线拟合/评价。费用按实例墙钟单独记录，小时价未知，不购买资源。
''')
    print('BACKEND_PREPARED',json.dumps({k:transition[k] for k in ['old_P0_HTTP200','old_P1_HTTP200','incomplete_attempts','unknown_outcomes','saved_responses']}),flush=True)
async def benchmark():
    idx={j['id']:j for j in r.jobs()};plan=c.read(O/'marlin_benchmark_plan.json');results=[]
    for name in ['M0','M1','M2','M3','M4']:
        if name=='M4' and results[-1]['requests_per_min']<1.1*results[-2]['requests_per_min']:break
        p=plan[name];internal='P0' if name=='M0' else name
        m=await r.run_stage([idx[i] for i in p['ids']],p['concurrency'],internal)
        m=dict(m,marlin_stage=name,backend_id=BACKEND);c.put(O/f'benchmark_{name}.json',m);results.append(m)
        if name=='M0':
            pp=r.parsed(idx[p['ids'][0]]);assert isinstance(pp['reasoning'],str) and pp['reasoning'].strip(),'MARLIN_REASONING_EMPTY'
            speed=dict(old_AWQ=c.read(OLD_O/'stage_P0.json'),marlin=m,reasoning_characters=len(pp['reasoning']),same_proposition=True,same_body=True,speed_not_model_capability=True)
            c.put(O/'single_request_speed_comparison.json',speed)
            if m['latency_max']>180:raise RuntimeError('AWQ_MARLIN_SINGLE_TOO_SLOW')
        assert m['stable'],'MARLIN_BENCHMARK_UNSTABLE_NO_FORMAL'
        if len(results)>2:assert m['latency_p90']<3*results[-2]['latency_p90'],'MARLIN_P90_UNCONTROLLED'
    chosen=results[1]
    for m in results[2:]:
        if m['requests_per_min']>=chosen['requests_per_min']*(1.1 if m['concurrency']>=8 else 1.):chosen=m
    done={j['id'] for j in idx.values() if r.success(j)};forecasts={};tiers={'A':(800,200),'B':(600,120),'C':(400,100)}
    for t,(n,d) in tiers.items():
        ids={j['id'] for j in idx.values() if j['stage']=='calibration'}|{x['id'] for x in c.lines(O/f'natural{n}.jsonl')}|{x['id'] for x in c.lines(O/f'diagnostic{d}.jsonl')}
        forecasts[t]=dict(total=len(ids),completed=len(ids&done),remaining=len(ids-done),predicted_hours=len(ids-done)/chosen['requests_per_min']/60*1.25)
    c.put(O/'concurrency_benchmark.json',dict(backend_id=BACKEND,stages=results,selected_concurrency=chosen['concurrency'],selected_rate=chosen['requests_per_min'],throughput_allowance=1.25,forecasts=forecasts,evaluation_accuracy_read=False))
    tier='A' if forecasts['A']['predicted_hours']<=3.5 else 'B' if forecasts['B']['predicted_hours']<=3.5 else 'C'
    if forecasts['C']['predicted_hours']>4:raise RuntimeError('R1_RUNTIME_TOO_HIGH')
    n,d=tiers[tier];ids=[j['id'] for j in idx.values() if j['stage']=='calibration']+[x['id'] for x in c.lines(O/f'natural{n}.jsonl')]+[x['id'] for x in c.lines(O/f'diagnostic{d}.jsonl')];assert done<=set(ids)
    if not (O/'tier_selection.json').exists():c.put(O/'tier_selection.json',dict(backend_id=BACKEND,tier=tier,natural=n,diagnostic=d,calibration=143,ids=ids,ids_sha256=c.digest(ids),concurrency=chosen['concurrency'],forecasts=forecasts,selected_utc=c.now(),formal_deadline_epoch=time.time()+4*3600,selection_uses_accuracy=False))
    print('MARLIN_TIER_FROZEN',tier,'concurrency',chosen['concurrency'],'hours',forecasts[tier]['predicted_hours'],flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['prepare','benchmark','formal','all','status']);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    if a.command=='prepare':prepare();return
    activate()
    if a.command=='status':print('MARLIN_HTTP200',sum(r.success(j) is not None for j in r.jobs()));return
    if not a.execute:print('DRY_RUN_NO_NETWORK');return
    assert not (P/'STOP_REQUESTED').exists(),'Explicit interrupted state; reconcile before removing stop marker'
    def stop_signal(*_):
        (P/'STOP_REQUESTED').write_text(c.now(),encoding='utf-8');print('STOP_REQUESTED: drain in-flight, no new sends',flush=True)
    signal.signal(signal.SIGINT,stop_signal)
    lock=P/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        if a.command in ['benchmark','all']:asyncio.run(benchmark())
        if a.command in ['formal','all']:
            asyncio.run(r.formal());print('BACKEND',BACKEND,'TIER',c.read(O/'tier_selection.json')['tier'],'WAIT_FOR_USER_GPU_SHUTDOWN_BEFORE_OFFLINE_ANALYSIS',flush=True)
    except BaseException as e:c.append(O/'execution_events.jsonl',dict(utc=c.now(),event='stopped',error=str(e),type=type(e).__name__));raise
    finally:lock.unlink(missing_ok=True)
if __name__=='__main__':main()
