"""Private remote entrypoint template; run only after explicit launch and GPU idle."""
from pathlib import Path
import json, subprocess, tarfile, time


def main():
    p = Path(__file__).resolve().parent
    if (p/'pid.json').exists(): raise RuntimeError('141 already launched; inspect instead of duplicate')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
        raise RuntimeError('GPU occupied; do not overlap any active GPU task')
    with tarfile.open(p/'bundle.tar.gz') as archive: archive.extractall(p,filter='data')
    job=json.loads((p/'data/job.json').read_text()); session=json.loads((p/'data/session.json').read_text())
    global_end=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']
    if global_end-time.time()<900: raise RuntimeError('Less than300 computation plus600 save reserve')
    log=(p/'run.log').open('ab')
    process=subprocess.Popen(['/root/verifact_image/envs/venv103/bin/python','-u','-B',str(p/'tasks/141_two_demos/controller141.py')],
                             cwd=p,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record=dict(task=141,scope=job['scope'],pid=process.pid,started=time.time(),no_shutdown=True)
    (p/'pid.json').write_text(json.dumps(record)+'\n'); print(json.dumps(record))


if __name__ == '__main__': main()
