"""Wait for the authorized idle window, resume frozen jobs, then close offline."""
import subprocess
import sys
import time
import common098 as c

def run(script, *args):
    result=subprocess.run([sys.executable,'-B',str(c.TASK/script),*args],cwd=c.ROOT)
    if result.returncode:
        raise RuntimeError(f'{script} exited {result.returncode}')

def main():
    plan=c.read(c.OUT/'execution_freeze.json')
    for rel,d in plan['files'].items():assert c.sha(c.ROOT/rel)==d,rel
    last=0
    while not c.is_idle():
        if time.monotonic()-last>=300:
            print(c.canonical(dict(status='WAITING_FOR_FROZEN_IDLE_WINDOW',utc=c.utc(),idle_UTC8='22:00-08:00',no_new_requests=True)),flush=True)
            last=time.monotonic()
        time.sleep(30)
    run('runtime098.py','remaining','--workers','6')
    run('analyze098.py')
    run('report098.py')
    run('selfcheck098.py')
    c.put(c.OUT/'complete.json',dict(utc=c.utc(),status='COMPLETE',report_sha256=c.sha(c.OUT/'report.md'),
          selfcheck_sha256=c.sha(c.OUT/'selfcheck.json'),analysis_sha256=c.sha(c.OUT/'analysis.json'),
          default_changed=False,committed=False,pushed=False,independent_audit=False))
    print(c.canonical(c.read(c.OUT/'complete.json')),flush=True)

if __name__=='__main__':main()
