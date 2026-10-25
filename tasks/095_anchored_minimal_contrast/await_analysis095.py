"""Generate final tables only after the authorized A queue has naturally drained."""
import subprocess,time,sys
import common095 as c

def call(script):subprocess.run([sys.executable,str(c.TASK/script)],cwd=c.ROOT,check=True)

if __name__=='__main__':
    deadline=time.monotonic()+4*3600
    while time.monotonic()<deadline:
        if any(r['stage']=='A_all_permitted_calls_finished' for r in c.lines(c.OUT/'progress.jsonl')):break
        time.sleep(30)
    else:raise RuntimeError('A completion marker missing; inspect running process before any analysis')
    assert not (c.PRIVATE/'run.lock').exists()
    call('analyze_baseline095.py');call('repeat_diagnostic095.py');call('cost095.py');call('plot095.py');call('report095.py');call('manuscript095.py')
    c.progress('analysis_ready','Actual final coverage, metrics, ledger, figures and draft written. Independent final review and self-check still required; not yet committed.')
    print('ANALYSIS_READY',flush=True)
