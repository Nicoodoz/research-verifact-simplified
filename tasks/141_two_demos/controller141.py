"""Watch only the141 child process; never stop another task or the instance."""
from pathlib import Path
import json, os, signal, subprocess, sys, time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tasks/139_full_repeat'))
from budget139 import deadlines
R = Path(__file__).resolve().parents[2]


def main():
    session = json.loads((R / 'data/session.json').read_text())
    job = json.loads((R / 'data/job.json').read_text())
    if subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
        raise RuntimeError('GPU occupied; do not overlap any active GPU task')
    timing = deadlines(time.time(), session, job)
    if timing['available_compute_seconds'] < 300:
        raise RuntimeError('Insufficient computation time plus600-second global save reserve')
    child = subprocess.Popen([sys.executable, '-u', '-B', str(R/'tasks/141_two_demos/worker141.py')],
                             cwd=R, start_new_session=True)
    timed_out = False
    try:
        code = child.wait(timeout=max(1, timing['compute_end']-time.time()+45))
    except subprocess.TimeoutExpired:
        timed_out = True; os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL); child.wait()
        code = 124
    (R/'controller_done.json').write_text(json.dumps(dict(task=141, exit_code=code,
        epoch=time.time(), watchdog_timeout=timed_out, deadlines=timing, no_shutdown=True))+'\n')
    raise SystemExit(code)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        output=R/'results';output.mkdir(exist_ok=True)
        (output/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,error=str(error),
            phase='controller',epoch=time.time(),no_shutdown=True))+'\n')
        (R/'controller_done.json').write_text(json.dumps(dict(task=141,exit_code=1,
            epoch=time.time(),no_shutdown=True))+'\n')
        raise
