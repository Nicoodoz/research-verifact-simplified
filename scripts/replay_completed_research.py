"""Replay completed019-021 from saved outputs into a new directory; no API/GPU."""
from pathlib import Path
from unittest.mock import patch
import argparse,json,shutil,socket,sys
ROOT=Path(__file__).resolve().parents[1]
TASKS={'019':'019_support_boundary_screen','020':'020_lambda2_patient_validation','021':'021_bge_localization'}
def block(*a,**k):raise RuntimeError('Offline replay: network forbidden')
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if src.is_dir():shutil.copytree(src,dst)
 else:shutil.copyfile(src,dst)
def safe_destination(task, destination):
 dest=Path(destination).resolve()
 if dest.exists():raise ValueError('Output must be a NEW directory')
 if dest.is_relative_to(ROOT) and not dest.is_relative_to(ROOT/'outputs/replays'):
  raise ValueError('Within this repository, output must be under outputs/replays/')
 if dest==ROOT/'outputs/replays':raise ValueError('Choose a named replay subdirectory')
 return dest

def check_bindings(task):
 path=ROOT/'reviews/artifacts/019_021_audit_20260919/audited_files_sha256.json'
 hashes=json.loads(path.read_text(encoding='utf-8'))
 import hashlib
 prefixes=('tasks/'+TASKS[task]+'/', 'outputs/'+TASKS[task]+'/')
 for name,expected in hashes.items():
  if name.startswith(prefixes):
   actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
   if actual!=expected:raise ValueError('Frozen file changed: '+name)
 if task=='021':
  from importlib.util import spec_from_file_location,module_from_spec
  spec=spec_from_file_location('verify021',ROOT/'tasks'/TASKS[task]/'verify021.py')
  mod=module_from_spec(spec);spec.loader.exec_module(mod)
  for name,expected in mod.EXPECTED_SOURCE.items():
   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('020 source changed: '+name)

def main():
 p=argparse.ArgumentParser();p.add_argument('--task',choices=TASKS,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 dest=safe_destination(a.task,a.output);original=ROOT/'outputs'/TASKS[a.task]
 sys.path.insert(0,str(ROOT/'tasks'/TASKS[a.task]))
 socket.socket.connect=block;socket.socket.connect_ex=block;socket.create_connection=block
 check_bindings(a.task)
 dest.mkdir(parents=True)
 prior_relative=Path.relative_to
 def relative(self,other,*args):
  try:return prior_relative(self,other,*args)
  except ValueError:
   if self.is_relative_to(dest) and Path(other)==ROOT:return self
   raise
 compared=[]
 with patch.object(Path,'relative_to',relative):
  if a.task=='019':
   import common019 as c,analysis019 as analysis
   for name in ['live_ledger.json','selection/preparation','selection/live','selection/cohort.csv','selection/cohort_manifest.json']:copy(original/name,dest/name)
   with patch.object(c,'OUT',dest):analysis.analyze('selection')
   pairs=[(p,dest/'selection/analysis_001'/p.name) for p in (original/'selection/analysis_001').iterdir() if p.name not in ('manifest.json','decision.json')]
   before=c.read(original/'selection_freeze.json');after=c.read(dest/'selection_freeze.json')
   before.pop('created_utc',None);after.pop('created_utc',None)
   assert before==after,'019 decision changed'
  elif a.task=='020':
   import common020 as c,analyze020 as analysis
   for name in ['live_ledger.json','protocol_001.md','new10/base_preparation_001','new10/preparation_002','new10_judge']:copy(original/name,dest/name)
   with patch.object(c,'OUT',dest):analysis.run()
   pairs=[(p,dest/'analysis_001'/p.name) for p in (original/'analysis_001').iterdir() if p.name!='manifest.json']
  else:
   import common021 as c,prepare_candidates_variant021 as candidates,prepare_pairs_variant021 as pairs_module,analyze_variant021 as analysis
   for name in ['local_vectors_fp32.npy','local_embedding_ids.json','local_rerank_scores_fp32emb_fp16rr_b32.jsonl']:copy(original/name,dest/name)
   with patch.object(c,'OUT',dest):
    with patch.object(sys,'argv',['candidates','--vectors','local_vectors_fp32.npy','--tag','fp32']):candidates.main()
    with patch.object(sys,'argv',['pairs','--tag','fp32']):pairs_module.main()
    with patch.object(sys,'argv',['analysis']):analysis.main()
   names=['local_candidates_fp32.jsonl','candidate_fp32_summary.json','rerank_pair_ids_fp32.jsonl','rerank_pair_fp32_summary.json','claim_comparison.csv','comparison_summary.json']
   pairs=[(original/n,dest/n) for n in names]
  for source,target in pairs:
   assert source.read_bytes()==target.read_bytes(),'Replay differs: '+source.name
   compared.append(source.relative_to(original).as_posix())
 (dest/'replay_summary.json').write_text(json.dumps(dict(task=a.task,status='PASS',compared_files=compared,API_calls=0,GPU_inference=False,
  note='021 generated report is a renderer snapshot; frozen editorial report is retained.'),indent=2)+'\n',encoding='utf-8')
 print('REPLAY_PASS',a.task,len(compared))
if __name__=='__main__':main()
