"""Bounded remote launcher/controller; never stops another task or the instance."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import tarfile
import time

PYTHON='/root/verifact_image/envs/venv103/bin/python'

def put(path, value):
    path.write_text(json.dumps(value)+'\n',encoding='utf-8')

def idle():
    return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()

def main():
    p=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser();parser.add_argument('--controller',action='store_true');args=parser.parse_args()
    if not args.controller:
        if (p/'pid.json').exists() or (p/'results').exists():
            raise RuntimeError('Existing144 launch/results: inspect rather than launch again')
        if not idle():raise RuntimeError('GPU occupied; leave current experiment running')
        with tarfile.open(p/'bundle.tar.gz') as archive:archive.extractall(p,filter='data')
        session=json.loads((p/'bundle/data/session.json').read_text())
        job=json.loads((p/'bundle/data/job.json').read_text())
        remaining=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']-time.time()
        if remaining < job['compute_limit_seconds']+job['save_reserve_seconds']:
            raise RuntimeError('Insufficient shared budget for bounded stage and saving')
        with (p/'controller.log').open('ab') as log:
            child=subprocess.Popen([PYTHON,'-u','-B',str(p/'start144.py'),'--controller'],cwd=p,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        record=dict(task=144,scope=job['scope'],pid=child.pid,started=time.time(),no_shutdown=True)
        put(p/'pid.json',record);print(json.dumps(record),flush=True);return
    if not idle():raise RuntimeError('GPU became occupied; no overlap allowed')
    b=p/'bundle';job=json.loads((b/'data/job.json').read_text());session=json.loads((b/'data/session.json').read_text())
    started=time.time();global_end=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']
    deadline=min(started+job['compute_limit_seconds'],global_end-job['save_reserve_seconds'])
    command=[PYTHON,'-u','-B',str(b/'score_worker.py'),'--execute','--bundle',str(b),
             '--session',str(b/'data/session.json'),'--compute-seconds',str(job['compute_limit_seconds']),
             '--save-reserve-seconds',str(job['save_reserve_seconds'])]
    with (p/'run.log').open('ab') as log:
        process=subprocess.Popen(command,cwd=p,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        put(p/'worker_pid.json',dict(pid=process.pid,started=started,deadline=deadline,command=command))
        terminated=False
        try:code=process.wait(timeout=max(1,deadline-time.time()))
        except subprocess.TimeoutExpired:
            terminated=True;process.terminate()
            try:code=process.wait(timeout=min(60,job['save_reserve_seconds']/2))
            except subprocess.TimeoutExpired:
                process.kill();code=process.wait(timeout=30)
    put(p/'controller_done.json',dict(task=144,scope=job['scope'],exit_code=code,
        time_limit_terminated=terminated,started=started,ended=time.time(),wall_seconds=time.time()-started,
        no_shutdown=True,no_release=True))

if __name__=='__main__':main()
