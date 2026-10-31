"""Observe and return139 artifacts; credentials accepted once through stdin only."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, json, os, shlex, subprocess, sys, tarfile, time
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat';O=R/'outputs/139_full_repeat'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=['screen160','old500','full1817'])
    parser.add_argument('--once',action='store_true');parser.add_argument('--no-analyze',action='store_true');args=parser.parse_args()
    dll=Path(sys.executable).parent/'Library/bin'
    handle=os.add_dll_directory(str(dll)) if dll.exists() else None
    sys.path.insert(0,str(R/'.local_models/103_lora_selection/tooling/ssh'));import paramiko
    auth=json.loads(sys.stdin.readline());client=None;scope=args.scope
    local=P/scope;local.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
    job=json.loads((local/'job.json').read_text());session=json.loads((local/'bundle/data/session.json').read_text())
    remote='/root/autodl-tmp/verifact139_full_repeat_'+scope
    probe="""from pathlib import Path
import json,subprocess,time
p=Path(REMOTE);v={}
for n in ['pid.json','results/progress.json','results/complete.json','results/failure.json','results/runtime_model_guard.json','controller_done.json']:
 f=p/n
 if f.exists():v[n]=json.loads(f.read_text())
v['controller_alive']=Path('/proc/'+str(v.get('pid.json',{}).get('pid',0))).exists()
v['gpu']=subprocess.getoutput('nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader')
v['compute']=subprocess.getoutput('nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader')
v['epoch']=time.time();print(json.dumps(v))
""".replace('REMOTE',repr(remote))
    def connect():
        nonlocal client
        if client:client.close()
        client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(auth['host'],port=auth['port'],username=auth['user'],password=auth['password'],
            timeout=20,banner_timeout=20,auth_timeout=20,look_for_keys=False,allow_agent=False)
    def execute(code):
        _,out,err=client.exec_command('/root/verifact_image/envs/venv103/bin/python -c '+shlex.quote(code),timeout=60)
        value=out.read().decode();error=err.read().decode()
        if out.channel.recv_exit_status():raise RuntimeError(error[-1200:])
        return value
    try:
        connect();previous=None;failures=0
        while True:
            try:
                state=json.loads(execute(probe));failures=0
                (local/'live_snapshot.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
                progress=state.get('results/progress.json',{});n=progress.get('completed',0);eta=progress.get('remaining_seconds')
                terminal='controller_done.json' in state or ('pid.json' in state and not state['controller_alive'])
                cost=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600
                stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
                lines=['#139 full_repeat实时进度','',stamp,'',
                    f"阶段{scope}：新增{n}/{job['expected_N']}；目标累计{n+job['prior_N']}/{job['target_N']}；状态{progress.get('stage','starting')}。",'',
                    ('正式首答推算剩余约'+str(round(eta/60,1))+'分钟。') if eta is not None else '尚无正式吞吐估计。','',
                    f'09:36:01窗口GPU累计约¥{cost:.3f}/20；本任务新增API0，原API累计0/80。',
                    f"本阶段最多{job['compute_limit_seconds']}秒计算另加{job['save_reserve_seconds']}秒保存；全局截止优先。",
                    'GPU：'+state['gpu']+'；计算进程：'+(state['compute'] or '无')+'。',
                    '失败：'+str(state.get('results/failure.json','无已确认失败。')),
                    '不自动关机、不释放、不重发、不截断。','']
                (O/'progress.md').write_bytes('\n'.join(lines).encode('utf-8'))
                cursor=(progress.get('stage'),n//10,terminal)
                if cursor!=previous:
                    print(json.dumps(dict(task=139,scope=scope,completed=n+job['prior_N'],target=job['target_N'],stage=progress.get('stage'),
                        ETA_min=None if eta is None else round(eta/60,1),GPU_CNY=round(cost,3),terminal=terminal)),flush=True);previous=cursor
                if terminal:
                    packaging="""from pathlib import Path
import tarfile
p=Path(REMOTE)
with tarfile.open(p/'return139.tar.gz','w:gz',compresslevel=1) as t:
 for f in (p/'results').rglob('*'):
  if f.is_file():t.add(f,arcname=f.relative_to(p/'results'),recursive=False)
 for name in ['controller_done.json','pid.json','run.log']:
  f=p/name
  if f.exists():t.add(f,arcname=name,recursive=False)
""".replace('REMOTE',repr(remote))
                    execute(packaging)
                    with client.open_sftp() as ftp:ftp.get(remote+'/return139.tar.gz',str(local/'return139.tar.gz'))
                    evidence=P/'evidence'/scope;evidence.mkdir(parents=True,exist_ok=True)
                    with tarfile.open(local/'return139.tar.gz') as archive:archive.extractall(evidence,filter='data')
                    analysis_code=None
                    if not args.no_analyze:
                        folders=[P/'evidence'/s/'full_repeat' for s in ['screen160','old500','full1817'] if (P/'evidence'/s/'full_repeat').exists()]
                        if folders:
                            command=[sys.executable,'-B',str(R/'tasks/139_full_repeat/analyze139.py'),'--scope',scope,'--results',*[str(f) for f in folders],'--out',str(O)]
                            if scope=='full1817':command.append('--bootstrap')
                            with (local/'analysis.log').open('ab') as log:
                                analysis_code=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT).returncode
                    print(json.dumps(dict(task=139,returned=True,analysis_exit=analysis_code,terminal=state.get('controller_done.json'))),flush=True)
                    break
                if args.once:break
                time.sleep(20)
            except (OSError,EOFError,paramiko.SSHException,RuntimeError):
                failures+=1;print(json.dumps(dict(observation_retry=failures)),flush=True)
                if failures>=5:raise
                time.sleep(5);connect()
    finally:
        if client:client.close()
        auth.clear()
        if handle:handle.close()


if __name__=='__main__':main()
