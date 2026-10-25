import subprocess,sys
import common031 as c
import api031 as a
def run():
    out=c.OUT/'execution_freeze_001.json';c.require(not out.exists(),'Execution freeze exists');tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(c.TASK),'-p','test031.py','-v'],cwd=c.ROOT,text=True,capture_output=True);c.write_text(c.OUT/'preflight_tests_001.txt',tests.stdout+tests.stderr);c.require(tests.returncode==0,'Tests failed')
    paths=list(c.TASK.glob('*.py'))+[c.OUT/'protocol_001.md',c.OUT/'freeze_001/manifest.json',c.OUT/'before_models/manifest.json',c.OUT/'materials_001/manifest.json'];paths += [a.old28.TASK/'common028.py',a.old28.api.ROOT/'tasks/024_lambda2_transfer_validation/core024.py',a.old28.api.ROOT/'tasks/024_lambda2_transfer_validation/transport_direct024.py']
    c.put(out,dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},budget_cap=80,passed_synthetic_tests=True,confirmation_GT_unread=True));print('Execution frozen; 5 preflight tests passed')
if __name__=='__main__':run()
