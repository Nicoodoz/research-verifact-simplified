"""Wait for the live peak-ceiling batch to drain, then run only frozen blind pilot."""
import time,subprocess,sys
import common095 as c

def call(*args):subprocess.run([sys.executable,str(c.TASK/'workflow095.py'),*args],cwd=c.ROOT,check=True)

if __name__=='__main__':
    while (c.PRIVATE/'run.lock').exists():time.sleep(20)
    events=c.lines(c.OUT/'progress.jsonl');done=[r for r in events if r['stage']=='baseline' and isinstance(r['note'],dict) and 'completed_new' in r['note']]
    assert done,'baseline did not exit through its normal completion path'
    call('run','--stage','construct_pilot','--workers','8')
    if not (c.PRIVATE/'pilot_constructed.jsonl').exists():call('checks','--pilot')
    call('run','--stage','check_pilot','--workers','8')
    if not (c.PRIVATE/'pilot_checked.jsonl').exists():call('collect','--pilot')
    c.progress('pilot_ready','Frozen16 blind constructor/checker pilot complete; no final Judge or performance evaluation sent. Content review next.')
    print('PILOT_READY',flush=True)
