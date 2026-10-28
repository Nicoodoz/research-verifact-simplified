"""108 bound remote watchdog and early AutoDL shutdown; never runs on Windows."""
from pathlib import Path
import argparse,json,os,platform,subprocess,time

def put(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    t.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode());os.replace(t,p)

def request_shutdown(work,reason,identity,start):
    if platform.system()!='Linux' or platform.node()!=identity:raise RuntimeError('Refuse shutdown outside the bound108 Linux instance')
    work=Path(work)
    put(work/'shutdown_requested.json',dict(epoch=time.time(),reason=reason,bound_instance=identity,
        billing_start_epoch=start,hourly_cny=.92,estimated_gpu_cny=(time.time()-start)*.92/3600,
        instance_released=False,disk_deleted=False,platform_billing_stop_confirmed=False))
    os.sync();program=Path('/usr/bin/shutdown')
    magic=program.open('rb').read(4);prefix=[] if magic.startswith((b'#!',b'\x7fELF')) else ['/bin/bash']
    for attempt in range(3):
        try:
            result=subprocess.run(prefix+[str(program),'-h','now'],capture_output=True,text=True,timeout=30)
            put(work/'shutdown_command_result.json',dict(epoch=time.time(),attempt=attempt+1,returncode=result.returncode,
                command_sent=True,platform_billing_stop_confirmed=False))
            os.sync()
            if result.returncode==0:return
        except (OSError,subprocess.TimeoutExpired) as exc:
            put(work/'shutdown_command_result.json',dict(epoch=time.time(),error_type=type(exc).__name__,command_sent=True,platform_billing_stop_confirmed=False))
            os.sync()
        time.sleep(5)
    raise RuntimeError('AutoDL shutdown command failed; platform deadline remains required')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['watch','finish'])
    p.add_argument('--work',type=Path,required=True);p.add_argument('--identity',required=True)
    p.add_argument('--billing-start',type=float,required=True);p.add_argument('--deadline',type=float,required=True)
    p.add_argument('--reason',default='normal_completion');a=p.parse_args()
    if platform.system()!='Linux' or platform.node()!=a.identity:raise RuntimeError('108 instance binding mismatch')
    if a.action=='finish':request_shutdown(a.work,a.reason,a.identity,a.billing_start);return
    finish_seen=None
    while True:
        now=time.time();put(a.work/'watchdog_heartbeat.json',dict(epoch=now,pid=os.getpid(),deadline_epoch=a.deadline,
            billing_start_epoch=a.billing_start,hourly_cny=.92,estimated_gpu_cny=(now-a.billing_start)*.92/3600,
            bound_instance=a.identity,platform_auto_shutdown_beijing='2026-10-29 05:00'))
        finish=a.work/'finish_requested.json'
        if finish.exists() and finish_seen is None:finish_seen=now
        if not finish.exists():finish_seen=None
        backup_ready=(a.work/'backup_ack.json').exists()
        if now>=a.deadline or (finish_seen is not None and (backup_ready or now-finish_seen>=120)):
            reason=json.loads(finish.read_text()).get('reason','normal_completion') if finish.exists() else 'independent_hard_deadline'
            request_shutdown(a.work,reason,a.identity,a.billing_start);return
        time.sleep(5)

if __name__=='__main__':main()
