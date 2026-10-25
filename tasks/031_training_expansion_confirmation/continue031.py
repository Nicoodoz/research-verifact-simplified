"""Continue completed retrieval through blind scoring/inference and fixed evaluation."""
import subprocess,sys
import common031 as c
def main():
    for p,h in c.read(c.OUT/'analysis_contract_001.json')['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Analysis contract changed')
    c.require(not (c.OUT/'live.lock').exists(),'Another031API process active')
    def call(script,*args):
        print(c.now(),script,*args,flush=True);subprocess.run([sys.executable,'-u','-B',str(c.TASK/script),*args],cwd=c.ROOT,check=True)
    call('resume031.py','score');call('resume031.py','auxiliary')
    if not (c.OUT/'features_001').exists():call('fit_predict031.py','features')
    if not (c.OUT/'inference_001').exists():call('fit_predict031.py','fit_predict')
    if not (c.OUT/'analysis_001').exists():call('analyze031.py')
    if not (c.OUT/'costs_001').exists():call('costs031.py')
    c.put(c.OUT/'execution_complete.json',dict(created_utc=c.now(),all_executable_phases_complete=True,report_and_selfcheck_pending=True,no_next_experiment=True));print('031 calls/inference/evaluation complete; ready for report and self-check',flush=True)
if __name__=='__main__':main()
