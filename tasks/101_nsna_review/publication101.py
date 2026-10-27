"""Verify public101 data and prepare isolated simplified snapshot; never commit/push automatically."""
from pathlib import Path
import argparse,json,shutil,subprocess
import common101 as c
KEEP={'report.md','detailed_tables.md','case_analysis.md','case_review_selection.json','format_diagnostics.json','main_table.csv','decision.json','cost_ledger.json','selfcheck.json','complete.json','execution_freeze.json','trigger_freeze.json','cache_engineering_amendment.json','development_source_note.md','development_interface_check.json','budget_plan.json','release_notes.md','supplemental_statistics.json','supplemental_statistics.md'}
def tracked(root):return subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0')[:-1]
def scan():
 prohibited={'claim','reference','body','body_text','reason','asserted_fact','evidence_quotes','correspondence','api_key','Authorization'};count=0
 def check(x,path):
  nonlocal count
  if isinstance(x,dict):
   for k,v in x.items():
    technical_reason=(path=='cache_engineering_amendment.json' and k=='reason' and isinstance(v,str) and v.startswith('prepare101 incorrectly defaulted an absent endpoint'))
    assert k not in prohibited or technical_reason,(path,k)
    check(v,path)
  elif isinstance(x,list):
   for v in x:check(v,path)
  count+=1
 for path in c.OUT.iterdir():
  if path.suffix=='.json':check(c.read(path),path.name)
  elif path.suffix=='.jsonl':
   for r in c.lines(path):check(r,path.name)
 print(c.canonical(dict(public_json_nodes_checked=count,no_clinical_payload_fields=True)))
def sync():
 target=(c.ROOT/'.local_models/101_publish_simplified').resolve();assert target.is_relative_to((c.ROOT/'.local_models').resolve()) and (target/'.git').exists()
 allowed=set(tracked(c.ROOT));existing=set(tracked(target));copied=0
 # Full repo index must already include all intended new101 files before preparing this snapshot.
 for rel in sorted(allowed):
  path=Path(rel)
  if path.parts[0]=='outputs':
   if path.parts[1]=='101_nsna_review':
    if path.name not in KEEP:continue
   elif rel not in existing:continue
  dest=(target/rel).resolve();assert dest.is_relative_to(target) and '.git' not in dest.relative_to(target).parts
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/rel,dest);copied+=1
 for rel in sorted(existing-allowed):
  if rel.startswith('outputs/'):continue
  dest=(target/rel).resolve();assert dest.is_relative_to(target) and '.git' not in dest.relative_to(target).parts
  dest.unlink()
 outside=[r for r in allowed if not r.startswith('outputs/')]
 assert all((target/r).exists() and c.sha(target/r)==c.sha(c.ROOT/r) for r in outside)
 print(c.canonical(dict(target=str(target),copied=copied,outside_outputs_identical=len(outside),outputs_policy='Existing key artifact list plus explicit101 KEEP; full original local data preserved')))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['scan','sync']);args=ap.parse_args();scan() if args.mode=='scan' else sync()
