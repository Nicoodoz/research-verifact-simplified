"""Run one bounded training/evaluation phase on an idle GPU; never shut down."""
from pathlib import Path
import json, os, signal, subprocess, sys, time

R = Path(__file__).resolve().parents[2]
session = json.loads((R / 'data/session.json').read_text())
job = json.loads((R / 'data/job.json').read_text())
if subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
    raise RuntimeError('GPU occupied; do not preempt the current task')
started = time.time()
global_end = session['start_epoch'] + session['duration_seconds']
compute_end = min(global_end - job['save_reserve_seconds'],
                  started + job['phase_limit_seconds'] - job['save_reserve_seconds'])
if compute_end - started < 1800:
    raise RuntimeError('Insufficient bounded time for this fixed phase')
(R / 'pid.json').write_text(json.dumps(dict(task=140, pid=os.getpid(), started=started,
                                          compute_end=compute_end, no_shutdown=True)))
child = subprocess.Popen([sys.executable, '-u', '-B', str(R / 'tasks/140_kl_anchor/worker140.py')],
                         cwd=R, start_new_session=True)
try:
    code = child.wait(timeout=max(1, compute_end - time.time() + 90))
except subprocess.TimeoutExpired:
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=90)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
    code = 124
(R / 'controller_done.json').write_text(json.dumps(dict(exit_code=code, epoch=time.time(), no_shutdown=True)))
raise SystemExit(code)
