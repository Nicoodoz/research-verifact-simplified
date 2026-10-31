"""Explicit remote capture-only launcher; never used by ordinary score mode."""
from pathlib import Path
import argparse
import json
import os
import signal
import subprocess
import tarfile
import time

PYTHON='/root/verifact_image/envs/venv103/bin/python'


def put(path,value):path.write_text(json.dumps(value)+'\n',encoding='utf-8')
def read(path):return json.loads(path.read_text())
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def window_end(session):
    return min(session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],
               session['start_epoch']+session.get('duration_seconds',float('inf')))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--controller',action='store_true');args=parser.parse_args()
    stage=Path(__file__).resolve().parent
    if not args.controller:
        if (stage/'pid.json').exists() or (stage/'results').exists():raise RuntimeError('Preserve prior launch and first answers; no automatic restart')
        if not idle():raise RuntimeError('GPU occupied; no overlap')
        with tarfile.open(stage/'bundle.tar.gz') as archive:archive.extractall(stage,filter='data')
        job=read(stage/'bundle/data/job.json');session=read(stage/'bundle/data/session.json')
        if (job['expected_inputs'],job['expected_calls'],job['compute_limit_seconds'],job['save_reserve_seconds'])!=(12,24,600,180):
            raise ValueError('Unexpected frozen capture pilot')
        started=time.time();end=window_end(session)
        if end-started<780:raise RuntimeError('Insufficient original shared window for600+180')
        # Freeze once before spawning; a worker restart cannot refresh this clock.
        job['absolute_compute_deadline']=min(started+600,end-180)
        put(stage/'bundle/data/job.json',job)
        with (stage/'controller.log').open('ab') as log:
            process=subprocess.Popen([PYTHON,'-u','-B',str(stage/'start_capture.py'),'--controller'],
                cwd=stage,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        record=dict(task='144_capture_pilot',pid=process.pid,started=started,
                    deadline=job['absolute_compute_deadline'],no_shutdown=True)
        put(stage/'pid.json',record);print(json.dumps(record),flush=True);return
    if not idle():raise RuntimeError('GPU became occupied; no overlap')
    job=read(stage/'bundle/data/job.json');started=time.time();deadline=job['absolute_compute_deadline']
    if deadline<=started:raise TimeoutError('Capture compute deadline already expired')
    command=[PYTHON,'-u','-B',str(stage/'bundle/worker.py'),'--execute','--bundle',str(stage/'bundle')]
    terminated=False
    with (stage/'run.log').open('ab') as log:
        process=subprocess.Popen(command,cwd=stage,stdin=subprocess.DEVNULL,stdout=log,
                                 stderr=subprocess.STDOUT,start_new_session=True)
        put(stage/'worker_pid.json',dict(pid=process.pid,started=started,deadline=deadline,command=command))
        try:code=process.wait(timeout=max(1,deadline-time.time()))
        except subprocess.TimeoutExpired:
            terminated=True;os.killpg(process.pid,signal.SIGTERM)
            try:code=process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);code=process.wait(timeout=30)
    put(stage/'controller_done.json',dict(task='144_capture_pilot',exit_code=code,started=started,
        ended=time.time(),wall_seconds=time.time()-started,time_limit_terminated=terminated,
        no_shutdown=True,no_release=True))


if __name__=='__main__':main()
