"""One persistent compute ledger across no-GPU/GPU sessions and restarts.

This CLI never rents, starts or contacts an instance. Future Linux watchdog may
stop ONLY its bound current instance, with 2 CNY headroom for shutdown latency.
"""
from pathlib import Path
import argparse
import os
import platform
import subprocess
import time
import common105 as c

def machine():
    path=Path('/etc/machine-id')
    return path.read_text().strip() if path.exists() else platform.node()

def total(state,now=None):
    now=time.time() if now is None else now
    charged=sum(s['cost_cny'] for s in state['closed_sessions'])+state.get('adjustments_cny',0)
    active=state.get('active')
    if active:
        if now<active['billing_start_epoch']:raise ValueError('Clock precedes billing start')
        charged+=(now-active['billing_start_epoch'])/3600*active['hourly_cny']
    return charged

def initialize(path):
    path=Path(path)
    if path.exists():raise FileExistsError('Never reset the task105 ledger')
    c.put(path,dict(task=105,cap_cny=20,operating_line_cny=18,API_cap_cny=0,new_disk_allowed=False,
                    closed_sessions=[],active=None,adjustments_cny=0,shutdown_reserve_cny=2,created_utc=c.utc()))

def begin(path,kind,hourly,start):
    state=c.read(path)
    if state['active'] is not None:raise ValueError('Settle the existing billing interval before beginning another')
    if hourly<0 or start>time.time() or kind not in {'nogpu','gpu'}:raise ValueError('Invalid actual platform quote/start')
    if total(state)>=state['operating_line_cny']:raise RuntimeError('Compute budget already exhausted')
    state['active']=dict(kind=kind,hourly_cny=hourly,billing_start_epoch=start,machine_id=machine())
    state.pop('shutdown_requested',None);c.put(path,state)
    finish=Path(path).parent/'finish_requested.json'
    if finish.exists():finish.unlink()

def end(path,end_epoch,confirmed):
    state=c.read(path);active=state['active']
    if not confirmed or active is None:raise ValueError('Actual platform billing end confirmation required; keep unknown interval open')
    if not active['billing_start_epoch']<=end_epoch<=time.time():raise ValueError('Invalid platform end time')
    cost=(end_epoch-active['billing_start_epoch'])/3600*active['hourly_cny']
    state['closed_sessions'].append(dict(active,billing_end_epoch=end_epoch,cost_cny=cost,platform_stop_confirmed=True))
    state['active']=None;state.pop('shutdown_requested',None);c.put(path,state)

def require(path,seconds=120,kind='gpu',watchdog=False):
    state=c.read(path);active=state.get('active')
    if not active or active['kind']!=kind or active['machine_id']!=machine():raise RuntimeError('No matching live billing interval')
    projected=total(state)+seconds/3600*active['hourly_cny']
    if state.get('shutdown_requested') or projected>state['operating_line_cny']:raise TimeoutError('Safe budget stop; persistent ledger retained')
    if watchdog:
        ready=c.read(Path(path).parent/'watchdog_ready.json')
        if ready['machine_id']!=machine() or ready['ledger']!=str(Path(path).resolve()) or time.time()-ready['heartbeat_epoch']>12:raise RuntimeError('Independent budget watchdog not live')
        command=Path('/proc')/str(ready['pid'])/'cmdline'
        if not command.exists() or b'budget105.py' not in command.read_bytes() or b'watch' not in command.read_bytes():raise RuntimeError('Budget watchdog process identity mismatch')
    return state

def shutdown_command(program=Path('/usr/bin/shutdown')):
    # AutoDL may ship a plain shell script without a shebang. An interactive
    # shell handles that, but subprocess.execve raises ENOEXEC. Retain native
    # ELF/shebang execution on installations where that is the actual file.
    program=Path(program)
    with program.open('rb') as handle:magic=handle.read(4)
    prefix=[] if magic.startswith((b'#!',b'\x7fELF')) else ['/bin/bash']
    return prefix+[str(program),'-h','now']

def watch(path):
    if platform.system()!='Linux':raise RuntimeError('Instance shutdown is Linux-only; never operate the Windows workstation')
    lock=Path(path).parent/'watchdog.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    while True:
        state=c.read(path);active=state.get('active')
        if active is None:lock.unlink();return
        if active['machine_id']!=machine():raise RuntimeError('Refuse to shut down another machine')
        c.put(Path(path).parent/'watchdog_ready.json',dict(pid=os.getpid(),ledger=str(Path(path).resolve()),machine_id=machine(),heartbeat_epoch=time.time()))
        if total(state)>=state['operating_line_cny'] or (Path(path).parent/'finish_requested.json').exists():
            state['shutdown_requested']=dict(utc=c.utc(),cost_at_request_cny=total(state),unknown_latency_reserve_cny=2,
                                               machine_id=machine(),platform_billing_stop_not_yet_verified=True)
            c.put(path,state);os.sync()
            for attempt in range(3):
                try:
                    command=shutdown_command()
                    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
                    receipt=dict(utc=c.utc(),attempt=attempt+1,command=command,returncode=result.returncode,
                                 stdout=result.stdout,stderr=result.stderr,platform_stop_verified=False)
                    c.put(Path(path).parent/'shutdown_result.json',receipt);os.sync()
                    if result.returncode==0:return
                except (OSError,subprocess.TimeoutExpired) as exc:
                    c.put(Path(path).parent/'shutdown_result.json',dict(utc=c.utc(),attempt=attempt+1,
                          error=type(exc).__name__,message=str(exc),platform_stop_verified=False));os.sync()
                time.sleep(5)
            raise RuntimeError('Shutdown command failed; stop this instance in platform console immediately; ledger remains open')
        time.sleep(3)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['init','begin','end','status','watch','finish'])
    parser.add_argument('--ledger',type=Path,required=True);parser.add_argument('--kind',choices=['nogpu','gpu'])
    parser.add_argument('--hourly',type=float);parser.add_argument('--billing-start',type=float);parser.add_argument('--billing-end',type=float)
    parser.add_argument('--platform-confirmed',action='store_true');args=parser.parse_args()
    if args.action=='init':initialize(args.ledger)
    elif args.action=='begin':
        if args.kind is None or args.hourly is None or args.billing_start is None:parser.error('Use actual quoted hourly rate and platform billing start')
        begin(args.ledger,args.kind,args.hourly,args.billing_start)
    elif args.action=='end':end(args.ledger,args.billing_end,args.platform_confirmed)
    elif args.action=='watch':watch(args.ledger)
    elif args.action=='finish':c.put(args.ledger.parent/'finish_requested.json',dict(utc=c.utc(),platform_stop_still_requires_verification=True))
    state=c.read(args.ledger)
    print(c.canonical(dict(compute_used_or_running_cny=total(state),hard_cap_cny=20,operating_line_cny=18,API_cny=0,active=state['active'],shutdown_requested=state.get('shutdown_requested'))))

if __name__=='__main__':main()

