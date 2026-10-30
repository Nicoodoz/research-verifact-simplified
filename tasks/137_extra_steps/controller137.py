from pathlib import Path
import json,os,signal,subprocess,sys,time
R=Path(__file__).resolve().parents[2]
s=json.loads((R/'data/session.json').read_text())
if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
remaining=s['start_epoch']+3600*s['GPU_cap_CNY']/s['hourly_CNY']-time.time()-120
if remaining<7200:raise RuntimeError('Insufficient wall-clock reserve for planned continuation')
p=subprocess.Popen([sys.executable,'-u','-B',str(R/'tasks/137_extra_steps/worker137.py'),'--job','data/job.json'],cwd=R,start_new_session=True)
try:code=p.wait(timeout=remaining)
except subprocess.TimeoutExpired:
 os.killpg(p.pid,signal.SIGTERM)
 try:p.wait(timeout=45)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 code=124
(R/'controller_done.json').write_text(json.dumps(dict(exit_code=code,epoch=time.time(),no_shutdown=True)))
raise SystemExit(code)
