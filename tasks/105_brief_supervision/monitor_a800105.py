"""Local30s monitor. SSH credentials are read once from stdin and never saved."""
import sys,os,json,time,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
binpath=Path(sys.executable).parent/'Library/bin'
dll=os.add_dll_directory(str(binpath)) if binpath.exists() else None
sys.path.insert(0,str(ROOT/'.local_models/103_lora_selection/tooling/ssh'))
import paramiko
auth=json.loads(sys.stdin.readline());auth['hostname']=auth.pop('host');zone=datetime.timezone(datetime.timedelta(hours=8))
OUT=ROOT/'outputs/105_brief_supervision';private=ROOT/'.local_models/105_brief_supervision/a800';private.mkdir(exist_ok=True)
REMOTE=r'''import json,time,os,subprocess
from pathlib import Path
r=Path('/root/autodl-tmp/verifact105');w=r/'results'
def read(p,default=None):
 try:return json.loads(p.read_text())
 except:return default
def lines(p):
 try:return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
 except:return []
state=read(r/'budget/ledger.json',{});active=state.get('active');now=time.time();cost=sum(s['cost_cny'] for s in state.get('closed_sessions',[]))+state.get('adjustments_cny',4.5039523163)
if active:cost+=(now-active['billing_start_epoch'])/3600*active['hourly_cny']
train={}
for arm in ['label_only','evidence_brief']:
 steps=lines(w/'train'/arm/'steps.jsonl');pointer=read(w/'train'/arm/'resume.json',{});steady=steps[1:] or steps
 train[arm]=dict(step=pointer.get('step',0),consumed=pointer.get('consumed',0),done=read(w/'train'/arm/'training_done.json') is not None,last_loss=steps[-1]['loss'] if steps else None,mean_step_seconds=sum(s['seconds'] for s in steady)/len(steady) if steady else None)
ev={}
for arm in ['base_judge','label_only','evidence_brief']:
 batches=[read(p,{}) for p in (w/'eval'/arm).glob('batch-*.json') if '.inflight.' not in p.name];n=sum(len(b.get('records',[])) for b in batches);seconds=sum(b.get('batch_seconds',0) for b in batches)
 ev[arm]=dict(N=n,batches=len(batches),seconds=seconds,remaining_minutes=(500-n)*seconds/n/60 if n else None)
try:gpu=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],text=True).strip()
except:gpu='unknown'
logs={}
for p in [Path('/root/restore105.log'),r/'gate105.log',r/'run105.log']:
 if p.exists():logs[p.name]=p.read_text(errors='replace')[-1800:]
loads=lines(w/'loads.jsonl')
print(json.dumps(dict(epoch=now,training=train,evaluation=ev,cost_cny=cost,ledger=state,gpu=gpu,current_load=loads[-1] if loads else None,restore=read(r/'image_restore_receipt.json'),gate=read(w/'gpu_gate.json'),plan=read(r/'a800_plan.json'),status=read(r/'a800_status.json'),logs=logs,complete=read(w/'execution_complete.json'))))
'''
while True:
 start=time.time();stamp=datetime.datetime.now(zone).isoformat(timespec='seconds')
 try:
  client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy());client.connect(**auth,look_for_keys=False,allow_agent=False,timeout=8,banner_timeout=8,auth_timeout=8)
  import shlex
  _,out,err=client.exec_command('/root/miniconda3/bin/python -c '+shlex.quote(REMOTE),timeout=12);raw=out.read().decode();error=err.read().decode();client.close();data=json.loads(raw)
  (private/'latest_snapshot.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  with (private/'snapshot_history.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
  text=['# 105实时进度（每30秒刷新）',f'\n更新时间：{stamp}；实例A800 80GB，¥7.98/小时；本次起点15:06。', '\n**关机方式：由用户手动关机。程序只保存/停止工作，不调用关机。**']
  status=data.get('status') or {};phase=data.get('current_load') or {};stage=status.get('stage','恢复环境与核验累计预算。')
  if phase.get('mode')=='train':stage='正式训练 '+phase['arm']+'（50步/392次消费）；'+('随后训练evidence_brief并执行三臂评价。' if phase['arm']=='label_only' else '完成后立即执行三臂评价。')
  elif phase.get('mode')=='eval':stage='正式评价 '+phase['arm']+'（500条）；仅统计工程进度，不据成绩修改方案。'
  if data.get('complete'):stage='训练与三臂评价已完成；正在核验和回传关键文件，随后通知用户手动关机。'
  if data['ledger'].get('shutdown_requested'):stage='任务已完成/停止，请查看最新通知并手动关机；GPU仍可能计费。'
  text+=['\n当前阶段：'+stage]
  plan=data.get('plan') or {};eta=plan.get('eta_text','尚无A800实测；旧完整估算约144分钟，高于当前可用预算，正在核验。')
  if plan and not data.get('complete'):
   tr=sum((50-s['step'])*(s['mean_step_seconds']/60 if s['mean_step_seconds'] is not None else plan['training_minutes']/100) for s in data['training'].values())
   estimates={'base_judge':plan['base_judge_minutes'],'label_only':plan['label_only_eval_minutes'],'evidence_brief':plan['evidence_brief_eval_minutes']}
   ev=sum(s['remaining_minutes'] if s['remaining_minutes'] is not None else estimates[k] for k,s in data['evaluation'].items());remaining=tr+ev+(6 if tr else 3)
   end=datetime.datetime.fromtimestamp(data['epoch']+remaining*60,zone).strftime('%H:%M')
   eta=f'约{remaining:.1f}分钟，预计{end}完成GPU计算及必要保存。拆分：剩余训练{tr:.1f}分钟、评价{ev:.1f}分钟、加载/保存余量{6 if tr else 3}分钟。未开始的臂用已测保守代理；早期编译会使估计波动。'
  if data.get('complete'):eta='GPU计算已完成，关键文件核验/回传进行中；不在GPU上等待离线指标分析。'
  text+=['\n预计剩余时间：'+str(eta)]
  text+=['\n|训练臂|优化器步|样本消费|最近loss|完成|','|---|---:|---:|---:|---|']
  for arm,s in data['training'].items():text.append(f"|{arm}|{s['step']}/50|{s['consumed']}/392|{s['last_loss'] if s['last_loss'] is not None else '—'}|{'是' if s['done'] else '否'}|")
  text+=['\n|评价臂|已保存预测|按已完成速度估计剩余|','|---|---:|---|']
  for arm,s in data['evaluation'].items():text.append(f"|{arm}|{s['N']}/500|{str(round(s['remaining_minutes'],1))+'分钟' if s['remaining_minutes'] is not None else '待实测'}|")
  text+=['\n关键适配器回传：'+ '；'.join(arm+' '+('已回传并通过SHA' if (private/'backup'/arm/'critical_backup_verified.json').exists() else '等待训练完成/回传中') for arm in ['label_only','evidence_brief'])+'。']
  cost=data['cost_cny'];elapsed=max(0,data['epoch']-1793171160);prior_minutes=37.954445
  rem=max(0,min((18-cost)/7.98*60,150-prior_minutes-elapsed/60))
  text += [f"\n累计已知计算估算：¥{cost:.4f}；另有¥2共享未知/人工关机余量。硬上限¥20，运行线¥18，累计GPU150分钟。",f'按现账本距停止工作线最多约{rem:.1f}分钟；历史停机区间仍待对账，不把未知费用清零。',f"\nGPU利用率/已用显存MiB/总显存MiB：`{data['gpu']}`。",'\n完整196条双臂、2轮及500条三臂保持冻结。当前不根据分类成绩调整方案。', '\n最新运行记录：']
  for name,log in data['logs'].items():
   safe=[x for x in log.splitlines() if not any(k in x.lower() for k in ['password','token=','api_key'])][-6:]
   text+=['\n`'+name+'`\n```text\n'+'\n'.join(safe)+'\n```']
  rendered='\n'.join(text).rstrip()+'\n'
  (ROOT/'.local_models/105_brief_supervision/实时情况.md').write_text(rendered,encoding='utf-8')
  (OUT/'实时进度.md').write_text(rendered,encoding='utf-8')
 except Exception as exc:
  with (private/'monitor_errors.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=stamp,error=type(exc).__name__,message=str(exc)))+'\n')
 time.sleep(max(1,30-(time.time()-start)))
