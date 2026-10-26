"""Read-only baseline, explicit interrupted transport receipts, then original frozen 098 runner."""
import json,sqlite3,subprocess,sys
import common100 as c
sys.path.insert(0,str(c.ROOT/'tasks/098_p90_native_confirmation'))
import common098 as old
import runtime098 as rt

def main():
 c.PRIVATE.mkdir(parents=True,exist_ok=True)
 assert not (c.OUT/'handoff_budget_snapshot.json').exists(),'Use the preserved snapshot and resume100.py instead'
 command="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python.*[.]exe$' -and $_.CommandLine -match '(runtime098|resume098|complete098)[.]py' } | Select-Object -ExpandProperty ProcessId"
 active=subprocess.check_output(['pwsh','-NoProfile','-Command',command]).decode().strip();assert not active,active
 con=sqlite3.connect(old.PRIVATE/'budget.sqlite');rows=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall()
 backup=sqlite3.connect(c.PRIVATE/'098_budget_before_resume.sqlite');con.backup(backup);backup.close();con.close()
 c.put(c.PRIVATE/'098_attempts_before_resume.json',rows)
 before=sum(r[3] for r in rows)
 freeze=c.read(old.OUT/'execution_freeze.json')
 for rel,h in freeze['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 recovered=[]
 for rid,num,arm,charge,status,folder in rows:
  p=c.ROOT/folder;req=c.read(p/'request.json');rp=p/'receipt.json'
  if not rp.exists():
   assert status==0 and abs(charge-req['reservation_cny'])<1e-9
   tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type='Interrupted_without_persisted_response',started_utc=req['utc'],ended_utc=c.utc(),elapsed_seconds=None,
           recovery_note='Forensic record of missing response; no server answer or billing evidence exists; full reservation retained')
   c.put(rp,dict(request_sha256=c.sha(p/'request.json'),transport=tr));value,basis=rt.accounting(req['job'],tr,req['reservation_cny'])
   c.put(p/'accounting.json',dict(cost_or_reserved_cny=value,basis=basis,reservation_cny=req['reservation_cny']))
   recovered.append(dict(request_id=rid,attempt=num,reserved_cny=charge))
  else:
   receipt=c.read(rp);assert receipt['request_sha256']==c.sha(p/'request.json')
   if status==200:assert receipt['transport']['http_status']==200
 rt.reconcile();after=rt.summary();assert abs(after['used_or_reserved_cny']-before)<1e-8
 succeeded=rt.completed();jobs=c.lines(old.PRIVATE/'jobs.jsonl')
 snapshot=dict(utc=c.utc(),start_main=subprocess.check_output(['git','rev-parse','main'],cwd=c.ROOT).decode().strip(),new_API_hard_cap_cny=130,operating_line_cny=125,abnormal_margin_cny=5,
  previous098_cost_and_unknown_cny=before,previous098_attempts=len(rows),previous098_HTTP200=sum(r[4]==200 for r in rows),previous098_successful_target_requests=sum(j['request_id'] in succeeded for j in jobs),
  task098_original_cumulative_cap_cny=50,task098_target_requests=len(jobs),remaining098_target_requests=sum(j['request_id'] not in succeeded for j in jobs),
  previous099_excluded_from_new_budget=True,old_unknown_reservations_retained=True,forensic_missing_response_records=recovered,
  immutable098_sha256={rel:c.sha(c.ROOT/rel) for rel in freeze['files']},default_env_sha256=c.sha(c.ROOT/'.env.aliyun'),GT_files_unchanged=True)
 c.put(c.OUT/'handoff_budget_snapshot.json',snapshot)
 lock=old.PRIVATE/'run.lock'
 if lock.exists():lock.rename(c.PRIVATE/'098_stale_run.lock')
 print(c.canonical(snapshot),flush=True)

if __name__=='__main__':main()
