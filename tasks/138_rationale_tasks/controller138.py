from pathlib import Path
import json,os,signal,subprocess,sys,time
R=Path(__file__).resolve().parents[2];s=json.loads((R/'data/session.json').read_text())
if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
limit=s['start_epoch']+s['duration_seconds']-time.time()-300
child=subprocess.Popen([sys.executable,'-u','-B',str(R/'tasks/138_rationale_tasks/worker138.py')],cwd=R,start_new_session=True)
try:code=child.wait(timeout=max(1,limit))
except subprocess.TimeoutExpired:
 os.killpg(child.pid,signal.SIGTERM)
 try:child.wait(timeout=45)
 except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
 code=124
(R/'controller_done.json').write_text(json.dumps(dict(exit_code=code,epoch=time.time(),no_shutdown=True)))
raise SystemExit(code)
