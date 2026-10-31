"""Rebase the existing CPU-only133 package onto the renewed authorization.

The frozen old package remains untouched. No GPU or network activity occurs.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,shutil,tarfile

R=Path(__file__).resolve().parents[2]
P=R/'.local_models/133_shuffle_repeat'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--start-epoch',type=float,required=True);args=ap.parse_args()
 run=P/'run20261031';bundle=run/'bundle';old=P/'bundle'
 if (run/'prepared.json').exists():raise RuntimeError('Prepared run already exists; inspect instead of overwriting')
 shutil.copytree(old,bundle,ignore=shutil.ignore_patterns('__pycache__'))
 session=dict(start_epoch=args.start_epoch,start_local=datetime.fromtimestamp(args.start_epoch,timezone(timedelta(hours=8))).isoformat(),
  duration_seconds=20/1.58*3600,GPU_cap_CNY=20.,hourly_CNY=1.58,API_cap_CNY=80.,API_used_CNY=0.,no_shutdown=True,no_release=True,
  authorization='User renewed original native-verification goal with an additional20 CNY GPU budget; original API80 remains cumulative.',
  prior_window_start_epoch=1793374800.,prior_GPU_to_new_authorization_CNY=(args.start_epoch-1793374800)*1.58/3600,
  unused_prior_GPU_balance_not_spent_in_this_window=True)
 put(run/'session.json',session);put(bundle/'data/shuffle_repeat/session.json',session)
 job=read(bundle/'data/shuffle_repeat/job.json');job.update(source107_adapter='/root/autodl-tmp/verifact133_repeat20261031/source107/checkpoint_a',
  phase_limit_seconds=21600,save_reserve_seconds=300,conditional_execution=False,
  replication='One preselected seed118027 and shuffled original2945 training IDs; fixed369, no best-seed or checkpoint selection',
  followup_evaluation='Paired plain104 and claim_repeat on the original20 patients; cache old baselines, retain first responses, no alpha interpolation')
 put(bundle/'data/shuffle_repeat/job.json',job);put(run/'job.json',job)
 put(bundle/'data/shuffle_repeat/decision.json',dict(execute=True,decision_epoch=args.start_epoch,
  reason='134 baselines complete;136 full risk tradeoff established;137 extra149 loses S/NA. Test one independent training order/seed and paired native inputs under renewed budget.',
  old132_and415_prerequisite_superseded='132 complete;415 cancelled with0 complete receipts; neither is an active launch prerequisite.',
  no_default_upgrade=True,no_shutdown=True))
 worker=bundle/'tasks/120_full_pool_sft/worker120.py';text=worker.read_text(encoding='utf-8')
 assert text.count('/root/autodl-tmp/verifact109/results/cache/')==2
 worker.write_text(text.replace('/root/autodl-tmp/verifact109/results/cache/','/root/autodl-tmp/verifact134/cache/'),encoding='utf-8')
 train=[json.loads(s) for s in (bundle/'data/shuffle_repeat/train.jsonl').read_text(encoding='utf-8').splitlines()]
 screen=[json.loads(s) for s in (bundle/'data/shuffle_repeat/screen.jsonl').read_text(encoding='utf-8').splitlines()]
 keys={r['id']:r for r in map(json.loads,(R/'.local_models/134_author_baselines/keys.jsonl').read_text(encoding='utf-8').splitlines())}
 assert len(train)==len({r['id'] for r in train})==2945 and len({r['sid'] for r in train})==32
 assert len(screen)==160 and {r['id'] for r in screen}==set(read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
 assert not {str(r['sid']) for r in train}&{str(keys[r['id']]['sid']) for r in screen}
 assert job['training']==read(P/'bundle/data/shuffle_repeat/job.json')['training']
 with tarfile.open(run/'bundle.tar.gz','w:gz',compresslevel=1) as t:
  for f in bundle.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
 summary=dict(status='READY_NOT_LAUNCHED',task=133,seed=118027,original_seed=117027,train_N=2945,train_patients=32,eval_patients=20,
  fixed_training_steps=369,source='same107 adapter, fresh Adam as120',
  train_data_source='reused original frozen133 package; no evaluation data or relabeling',
  first_evaluation_N=160,first_evaluation_panels={'natural':128,'pressure':32},
  target_evaluation_N_per_input=1817,inputs=['plain104','claim_repeat'],
  cache_only_patch='Existing134 compilation-cache path replaces retired109 cache path; training algorithm unchanged.',
  checkpoint_selection='fixed369; no selection by evaluation',
  budget=session,estimated_training_hours=3.85,estimated_with_two_input_full_evaluation_and_return_hours=[5,6],
  baseline_inference_repeated=False,source_weights_downloaded=False)
 put(run/'prepared.json',summary);put(R/'outputs/133_shuffle_repeat/renewed_preparation.json',summary)
 print(json.dumps({k:summary[k] for k in ['status','train_N','fixed_training_steps','first_evaluation_N','target_evaluation_N_per_input','inputs']},ensure_ascii=False))

if __name__=='__main__':main()
