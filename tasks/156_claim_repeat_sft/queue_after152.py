"""Wait for existing152; generate100 minimal reasons; then run matched369 SFT."""
from pathlib import Path
import json,time,subprocess,os
BASE=Path('/root/autodl-tmp');PY='/root/verifact_image/envs/venv103/bin/python'
P=BASE/'verifact156_claim_repeat_sft'
def read(p):return json.loads(Path(p).read_text())
def put(p,v):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2)+'\n');tmp.replace(p)
def main():
    if (P/'queue_pid.json').exists():raise FileExistsError('Queue already registered; inspect prior PID')
    put(P/'queue_pid.json',dict(pid=os.getpid(),started=time.time(),no_shutdown=True))
    end=read(P/'data/session.json')['end_epoch'];previous=BASE/'verifact152_demo_na_full1817'
    while not (previous/'controller_done.json').exists():
        if (previous/'results/failure.json').exists():raise RuntimeError('152 failed; preserve results before new GPU work')
        if time.time()+17400+1200>end:raise TimeoutError('Insufficient remaining window for full scheduled training')
        put(P/'queue_progress.json',dict(stage='waiting152',epoch=time.time(),no_shutdown=True));time.sleep(15)
    if read(previous/'controller_done.json')['exit_code']!=0:raise RuntimeError('152 nonzero; inspect')
    reason=BASE/'verifact158_minimal_reason'
    if (reason/'results/runtime.json').exists():raise FileExistsError('158 already attempted')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('Unexpected GPU occupancy')
    put(P/'queue_progress.json',dict(stage='reason158',epoch=time.time(),no_shutdown=True))
    with (reason/'controller.log').open('ab') as f:
        child=subprocess.Popen([PY,'-u','-B',str(reason/'worker158.py')],cwd=reason,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        put(reason/'pid.json',dict(pid=child.pid,started=time.time(),parent_queue=os.getpid()))
        try:code=child.wait(timeout=min(1080,end-time.time()-180))
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            raise TimeoutError('158 computation/save limit')
    if code or not (reason/'results/complete.json').exists():raise RuntimeError('158 incomplete; inspect before training')
    if (P/'runtime156.json').exists():raise FileExistsError('156 already attempted; inspect preserved clock')
    if time.time()+17400+180>end:raise TimeoutError('Insufficient full369 scheduled window')
    put(P/'queue_progress.json',dict(stage='training156',epoch=time.time(),no_shutdown=True))
    with (P/'controller.log').open('ab') as f:
        code=subprocess.call([PY,'-u','-B',str(P/'controller156.py')],cwd=P,stdout=f,stderr=subprocess.STDOUT)
    if code:raise RuntimeError('156 controller failed: '+str(code))
    put(P/'queue_complete.json',dict(epoch=time.time(),no_shutdown=True,no_release=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        put(P/'queue_failure.json',dict(type=type(error).__name__,error=str(error),epoch=time.time(),no_shutdown=True));raise
