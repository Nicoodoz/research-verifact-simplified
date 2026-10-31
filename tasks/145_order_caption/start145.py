"""Private remote entrypoint template; run only after explicit launch and GPU idle."""
from pathlib import Path
import json, subprocess, tarfile, time


def main():
    p = Path(__file__).resolve().parent
    if (p/'pid.json').exists(): raise RuntimeError('145 already launched; inspect instead of duplicate')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
        raise RuntimeError('GPU occupied; do not overlap any active GPU task')
    with tarfile.open(p/'bundle.tar.gz') as archive: archive.extractall(p,filter='data')
    job=json.loads((p/'data/job.json').read_text()); session=json.loads((p/'data/session.json').read_text())
    global_end=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']
    if 'duration_seconds' in session: global_end=min(global_end,session['start_epoch']+session['duration_seconds'])
    if global_end-time.time()<job['compute_limit_seconds']+job['save_reserve_seconds']: raise RuntimeError('Insufficient full frozen compute and save window')
    log=(p/'run.log').open('ab')
    process=subprocess.Popen(['/root/verifact_image/envs/venv103/bin/python','-u','-B',str(p/'tasks/145_order_caption/worker145.py')],
                             cwd=p,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record=dict(task=145,scope=job['scope'],pid=process.pid,started=time.time(),no_shutdown=True)
    (p/'pid.json').write_text(json.dumps(record)+'\n'); print(json.dumps(record))


if __name__ == '__main__': main()
