"""Close098 exactly, choose the authorized branch, then complete one100 evaluation."""
import subprocess,sys
import common100 as c
def run(task,script,*args):
 p=c.ROOT/'tasks'/task/script
 subprocess.run([sys.executable,'-B',str(p),*args],cwd=c.ROOT,check=True)
def main():
 old='098_p90_native_confirmation'
 assert not (c.ROOT/'.local_models'/old/'run.lock').exists()
 for script in ['analyze098.py','report098.py','selfcheck098.py']:run(old,script)
 out=c.ROOT/'outputs'/old;d=c.read(out/'decision.json');cost=c.read(out/'cost_ledger.json')
 c.put(out/'complete.json',dict(utc=c.utc(),status='COMPLETE',report_sha256=c.sha(out/'report.md'),selfcheck_sha256=c.sha(out/'selfcheck.json'),analysis_sha256=c.sha(out/'analysis.json'),
   completion_under_new_instruction=True,original_frozen_materials_preserved=True,initial_snapshot_already_published=True,completion_committed=False,completion_pushed=False,default_changed=False,independent_audit=False))
 branch='cross_model' if d['recommend_replace_C'] else 'evidence'
 c.put(c.OUT/'branch_decision.json',dict(utc=c.utc(),branch=branch,**{'098_complete':True},decision098_sha256=c.sha(out/'decision.json'),recommend_replace_C=d['recommend_replace_C'],
  reason='All original O/Q/C and pressure/repetition checks passed' if branch=='cross_model' else '098 did not simultaneously satisfy original O/Q/C utility and robustness checks',
  final098_cost_or_reserved_cny=cost['used_or_reserved_cny'],new098_cost_or_reserved_cny=cost['used_or_reserved_cny']-c.read(c.OUT/'handoff_budget_snapshot.json')['previous098_cost_and_unknown_cny']))
 print(c.canonical(dict(branch=branch,decision098=d)),flush=True)
 if branch=='cross_model':
  run(c.TASK.name,'runtime100.py','cross_model_confirmation','--workers','4');run(c.TASK.name,'analyze100.py','cross_model_confirmation')
 else:
  run(c.TASK.name,'runtime100.py','development','--workers','4');run(c.TASK.name,'analyze100.py','development')
  if c.read(c.OUT/'development_decision.json')['winner'] is not None:
   run(c.TASK.name,'runtime100.py','confirmation','--workers','4');run(c.TASK.name,'analyze100.py','confirmation')
 print('Authorized paid phases complete; finalize reports and selfchecks without new experiments',flush=True)
if __name__=='__main__':main()
