"""Continue original B after construction closes, then fill remaining permitted gap."""
import subprocess,sys
import common095 as c
def call(script,*args):subprocess.run([sys.executable,str(c.TASK/script),*args],cwd=c.ROOT,check=True)
if __name__=='__main__':
    assert c.read(c.OUT/'construction_stop.json')['decision']=='STOP_C_FINAL_JUDGE_CONTINUE_A_F'
    call('run095_v3.py','baseline','--workers','16')
    call('finish_baseline095.py')
    c.progress('A_all_permitted_calls_finished','Original fixed-ID B completion queues drained; inspect real coverage, do not infer completeness from this marker alone.')
    print('A_QUEUES_FINISHED',flush=True)
