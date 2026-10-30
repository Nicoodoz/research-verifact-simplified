"""Explicit Linux launch entry; no SSH, purchase, shutdown, or import side effects."""
from pathlib import Path
import argparse
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', default='data/balanced_pool_sft122.json')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if os.name != 'posix':
        raise RuntimeError('Launch only on the explicitly authorized existing Linux instance')
    path = Path(args.job)
    if not path.is_absolute():
        path = ROOT/path
    job = common.read(path)
    session = common.read(ROOT/job['session_path'])
    out = ROOT/'results'/job['name']
    out.mkdir(parents=True, exist_ok=True)
    if (out/'complete.json').exists():
        raise RuntimeError('122 already complete; do not repeat accepted evaluation')
    if (out/'pid.json').exists():
        previous = common.read(out/'pid.json')
        cmdline = Path(f"/proc/{previous['pid']}/cmdline")
        if cmdline.exists() and b'worker122.py' in cmdline.read_bytes():
            raise RuntimeError('Existing122 worker is still alive')
        if not args.resume:
            raise RuntimeError('Previous attempt exists; inspect it and explicitly pass --resume')
    deadline = min(session['start_epoch']+session['duration_seconds'],
                   session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'],
                   time.time()+job['phase_limit_seconds'])
    if time.time() >= deadline-job['save_reserve_seconds']:
        raise TimeoutError('Authorized122 execution window is already exhausted')
    active = subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
    if active:
        raise RuntimeError('GPU already has a compute process; do not overlap119 or another job')
    with (out/'worker.log').open('ab') as log:
        process = subprocess.Popen([sys.executable, '-u', str(ROOT/'tasks/122_balanced_pool_sft/worker122.py'),
                                    '--job', str(path)], cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        common.put(out/'pid.json', dict(pid=process.pid, controller_pid=os.getpid(),
                   start_epoch=time.time(), name=job['name'], deadline_epoch=deadline))
        try:
            while process.poll() is None and time.time() < deadline-90:
                time.sleep(2)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        common.put(out/'stopped.json', dict(exit_code=process.returncode, epoch=time.time(),
                   no_shutdown=True, no_release=True, instance_may_still_be_billing=True))
        return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
