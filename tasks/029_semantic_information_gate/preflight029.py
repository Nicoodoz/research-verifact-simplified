"""Synthetic tests and input freeze, no actual 029 model evaluation."""
import subprocess,sys
import common029 as c
import prepare029
def run():
    c.offline();dest=c.OUT/'preflight_001';c.require(not dest.exists(),'Preflight already exists');dest.mkdir(parents=True)
    result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(c.TASK),'-p','test029.py','-v'],cwd=c.ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    c.write_text(dest/'tests.txt',result.stdout+result.stderr);c.put(dest/'status.json',dict(synthetic_tests_exit_code=result.returncode,created_utc=c.now(),environment=c.environment(),real_data_fits=0))
    c.require(result.returncode==0,'Synthetic tests failed; do not launch')
    prepare029.run();print('029 preflight and input freeze passed; ready for a single unattended launch')
if __name__=='__main__':run()
