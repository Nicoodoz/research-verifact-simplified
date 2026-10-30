"""Prepare a fixed149-step continuation of120; does not start training."""
from pathlib import Path
import ast,json,shutil,sys,tarfile,time
R=Path(__file__).resolve().parents[2];P=R/'.local_models/137_extra_steps';B=P/'bundle';T=R/'tasks/137_extra_steps';O=R/'outputs/137_extra_steps'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from data105 import training_plan
source=R/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/train'
pointer=c.read(source/'resume.json');slot=source/pointer['slot'];complete=c.read(slot/'checkpoint_complete.json')
assert (pointer['step'],pointer['consumed'])==(369,2945)==(complete['step'],complete['consumed'])
assert (slot/'training_state.pt').stat().st_size>300_000_000
data=R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120'
rows=c.rows(data/'train.jsonl');original_plan=c.read(data/'plan.json');plan=training_plan([r['id'] for r in rows],2,8)[:518]
assert plan[:369]==original_plan and len(plan)==518 and plan[-1]['consumed']==4137
evalkeys=c.rows(R/'.local_models/134_author_baselines/keys.jsonl')
train_sids={str(r['sid']) for r in rows};eval_sids={str(r['sid']) for r in evalkeys}
assert len(rows)==2945 and len(train_sids)==32 and len(eval_sids)==20 and not train_sids&eval_sids
T.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
worker=(R/'.local_models/136_claim_repeat_transfer/continuation/worker_template.py').read_text(encoding='utf-8');ast.parse(worker)
(T/'worker137.py').write_text(worker,encoding='utf-8')
controller='''from pathlib import Path
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
'''
ast.parse(controller);(T/'controller137.py').write_text(controller,encoding='utf-8')
for src,dest in [(data/'train.jsonl',B/'data/train.jsonl'),(data/'lengths.jsonl',B/'data/lengths.jsonl'),
 (R/'.local_models/136_claim_repeat_transfer/claim_repeat_screen160/bundle/data/inputs.jsonl',B/'data/screen.jsonl')]:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
c.put(B/'data/plan.json',plan)
screen=c.rows(B/'data/screen.jsonl');assert len(screen)==160 and not set(r['id'] for r in screen)&set(r['id'] for r in rows)
c.putl(B/'data/screen_lengths.jsonl',[dict(id=r['id'],prompt_token_sha256=r['prompt_token_sha256']) for r in screen])
session=c.read(R/'.local_models/134_author_baselines/session.json');session['duration_seconds']=3600*session['GPU_cap_CNY']/session['hourly_CNY'];c.put(B/'data/session.json',session)
oldjob=c.read(R/'.local_models/120_full_pool_sft/job.json')
job=dict(oldjob,task=137,name='extra_steps',candidate='extra_steps',source120_adapter='source120/train/'+pointer['slot'],source_work='source120/train',
 source_fingerprint=pointer['fingerprint'],source_adapter_sha256=complete['files']['adapter_model.safetensors'],
 train_path='data/train.jsonl',lengths_path='data/lengths.jsonl',plan_path='data/plan.json',screen_inputs_path='data/screen.jsonl',
 screen_lengths_path='data/screen_lengths.jsonl',session_path='data/session.json',phase_limit_seconds=8100,save_reserve_seconds=300,
 additional_presentations=1192,input_transform='claim_repeat',source_training_step=369,target_training_step=518,
 checkpoint_selection='fixed final518; no selection from evaluation',conditional_execution=False)
job.pop('source107_adapter',None);job['training']=dict(oldjob['training'],epochs=2,total_steps=518,fresh_Adam=False)
c.put(B/'data/job.json',job);c.put(P/'job.json',job)
for rel in ['tasks/137_extra_steps/worker137.py','tasks/137_extra_steps/controller137.py','tasks/105_brief_supervision/common105.py',
 'tasks/105_brief_supervision/data105.py','tasks/105_brief_supervision/loss105.py','tasks/105_brief_supervision/parse105.py',
 'tasks/107_support_aux/checkpoint107.py','tasks/104_supervision_evidence/training104.py','tasks/136_claim_repeat_transfer/prompt136.py']:
 dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
dest=B/'source120/train';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(source/'resume.json',dest/'resume.json')
for f in slot.iterdir():
 if f.is_file() and f.name not in ('adapter_model.safetensors','training_state.pt'):
  d=dest/pointer['slot']/f.name;d.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,d)
with tarfile.open(P/'bundle137.tar.gz','w:gz',compresslevel=1) as t:
 for f in B.rglob('*'):
  if f.is_file():t.add(f,arcname=f.relative_to(B),recursive=False)
 t.add(slot/'training_state.pt',arcname='source120/train/'+pointer['slot']+'/training_state.pt')
summary=dict(status='PREPARED_NOT_TRAINED',source_step=369,target_step=518,additional_steps=149,new_presentations=1192,
 train_pool_N=2945,gradient_patients=32,evaluation_patients=20,patient_overlap=0,evaluation_N=160,evaluation_input='unchanged claim_repeat',
 original_GT_preserved=True,optimizer_scheduler_rng_resume=True,new_class_weights=False,new_reason_supervision=False,
 source_adapter=complete['files']['adapter_model.safetensors'],source_optimizer_bytes=(slot/'training_state.pt').stat().st_size,
 GPU_global_start=session['start_local'],GPU_cap_CNY=16,API_cap_CNY=80,API_used_CNY=0,
 estimated_training_hours=1.56,estimated_initial_total_hours=1.96,estimated_initial_cost_CNY=3.1,no_shutdown=True)
c.put(O/'preparation.json',summary);c.put(P/'preparation.json',summary)
print(c.canonical(summary))
