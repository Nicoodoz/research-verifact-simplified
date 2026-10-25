"""Run synthetic checks, then freeze inputs; no real-data Gate fitting."""
import subprocess,sys
import common030 as c
import prepare030
def main():
    c.offline();out=c.OUT/'preflight_001';c.require(not out.exists(),'Preflight exists; preserve original attempt');out.mkdir(parents=True)
    p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(c.TASK),'-p','test030.py','-v'],cwd=c.ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    c.write_text(out/'tests.txt',p.stdout+p.stderr);c.put(out/'status.json',dict(created_utc=c.now(),exit_code=p.returncode,environment=c.environment(),real_030_fits=0));c.require(p.returncode==0,'Synthetic preflight failed; not frozen or launched');prepare030.run();print('030 preflight passed and frozen; ready to launch once')
if __name__=='__main__':main()
