"""Freeze inference and analysis before new031 Judge outputs and any confirmation GT."""
import subprocess,sys
import common031 as c
def run():
    c.require(not (c.OUT/'analysis_contract_001.json').exists(),'Analysis contract exists')
    c.require(not (c.OUT/'candidate_freeze_001').exists() and not (c.OUT/'inference_001').exists(),'Must freeze before new candidate/confirmation results')
    p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(c.TASK),'-p','test_analysis031.py','-v'],cwd=c.ROOT,capture_output=True,text=True);c.write_text(c.OUT/'analysis_tests_001.txt',p.stdout+p.stderr);c.require(p.returncode==0,'Analysis tests failed')
    deps=[c.TASK/'fit_predict031.py',c.TASK/'analyze031.py',c.TASK/'test_analysis031.py',c.OUT/'protocol_001.md',c.base.TASK/'learning029.py',c.base.TASK/'common029.py'];c.put(c.OUT/'analysis_contract_001.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},new_Judge_responses_seen=False,confirmation_GT_connected=False));print('Four inference/statistics contract tests passed; analysis frozen')
if __name__=='__main__':run()
