
"""032 audit: all saved heads, OOF selection and frozen NLI input/cache bindings."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='4'
from pathlib import Path
import json,hashlib,sys,collections,shutil
import numpy as np
import torch
root=Path(__file__).resolve().parents[3];a=Path(__file__).parent
sys.path.insert(0,str(root/'tasks/032_evidence_relation_correction'))
import common032 as c,learning032 as l,nli032
c.block_network();torch.set_num_threads(4)
history={}
for p in (root/'reviews/artifacts').glob('*/audited_files_sha256.json'):history.update(json.loads(p.read_text()))
assert all(c.sha(root/p)==v for p,v in history.items())
rows,data=l.load_arrays();cfg=c.read(c.OUT/'preparation_001/config.json');folds=c.read(c.OUT/'preparation_001/folds.json')
split=c.read(root/'outputs/031_training_expansion_confirmation/planning_001/split.json')
train=np.array([i for i,r in enumerate(rows) if r['split']=='train']);test=np.array([i for i,r in enumerate(rows) if r['split']=='confirmation'])
assert len(rows)==3675 and len(train)==2527 and len(test)==1148
assert {rows[i]['subject_id'] for i in train}==set(split['original16']+split['expansion12'])
assert {rows[i]['subject_id'] for i in test}==set(split['confirmation12'])
expected_order=sorted(split['original16']+split['expansion12'],key=lambda s:hashlib.sha256(json.dumps(['032-train-fold-v1',s],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
for k,f in enumerate(folds):
 assert f['validation_patients']==expected_order[k::4]
 assert f['training_patients']==[s for s in expected_order if s not in f['validation_patients']]
gt={r['proposition_id']:r['human_gt'] for r in c.lines(c.OUT/'preparation_001/training_labels.jsonl')}
assert set(gt)=={rows[i]['proposition_id'] for i in train}
for p,h in c.read(c.OUT/'preparation_001/manifest.json')['sources'].items():assert c.sha(root/'outputs'/p)==h
freeze=c.read(c.OUT/'training_001/freeze.json')
for p,h in freeze['code'].items():assert c.sha(c.TASK/p)==h
assert c.sha(c.OUT/'preparation_001/inputs_blind.jsonl')==freeze['input_sha256']
assert c.sha(c.OUT/'preparation_001/training_labels.jsonl')==freeze['training_labels_sha256']
sel=c.read(c.OUT/'training_001/selections.json');inf=c.read(c.OUT/'inference_001/manifest.json')
assert freeze['created_utc']<c.read(c.OUT/'training_001/selection_freeze.json')['created_utc']<inf['created_utc']<c.read(c.OUT/'analysis_001/GT_connection.json')['created_utc']
# Original claims/references match audited sources, never augmented beyond C48.
materials={r['proposition_id']:r for p in ['031_training_expansion_confirmation/judge_inputs_001/materials.jsonl','026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl'] for r in c.lines(root/'outputs'/p)}
for j in c.lines(root/'outputs/024_lambda2_transfer_validation/preparation_001/jobs.jsonl'):
 v=json.loads(j['body']['messages'][-1]['content']);materials.setdefault(j['proposition_id'],dict(text=v['proposition'],reference=v['reference']))
assert all(r['text']==materials[r['proposition_id']]['text'] and r['reference']==materials[r['proposition_id']]['reference'] for r in rows)
asset=c.read(c.OUT/'model_manifest.json');modelpath=c.CACHE/'deberta_v3_nli'
assert asset['revision']==cfg['nli_revision']
for p,v in asset['files'].items():assert c.sha(modelpath/p)==v['sha256']
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained(str(modelpath),local_files_only=True,trust_remote_code=False)
pairs,bags,scope=nli032.build_pairs(rows,tok,cfg)
assert bags==c.lines(c.OUT/'nli_001/bags.jsonl') and scope==c.read(c.OUT/'nli_001/scope.json')
assert len(pairs)==54236
fingerprint=c.digest([asset['files'],[p['key'] for p in pairs],cfg['projection_seed'],cfg['projection_dimensions']])
assert fingerprint==c.read(c.OUT/'nli_001/manifest.json')['pair_cache_fingerprint']
assert c.sha(c.CACHE/'bags.npz')==c.read(c.OUT/'nli_001/manifest.json')['bags_sha256']
features=np.load(c.CACHE/'pair_cache/features.npy',mmap_mode='r');done=np.load(c.CACHE/'pair_cache/done.npy',mmap_mode='r')
assert np.all(done==1) and np.isfinite(features).all()
assert np.allclose(features[:,:3].sum(1),1,atol=1e-6)
assert np.allclose(np.log(np.maximum(features[:,:3],1e-7)),features[:,3:6],atol=2e-6)
assert np.allclose(np.linalg.norm(features[:,6:],axis=1),1,atol=1e-5)
for i,bag in enumerate(bags):
 n=len(bag['members']);assert n>0 and data['mask'][i].sum()==n
 for j,m in enumerate(bag['members']):
  assert np.array_equal(data['x'][i,j,:38],features[m['pair']])
  assert data['x'][i,j,38]==m['kind'] and abs(data['x'][i,j,39]-m['coverage'])<1e-7
 # Each evidence record's windows cover the full evidence-token range with no gaps.
 views=collections.defaultdict(list)
 for m in bag['members']:views[(m['kind'],tuple(m['records']))].append((m['token_start'],m['token_end']))
 for spans in views.values():
  spans.sort();assert spans[0][0]==0
  assert all(spans[k+1][0]<=spans[k][1] for k in range(len(spans)-1))
# Replay all CV/final models, check training-only normalization independently.
models=0;max_delta=0.
def replay(folder,ids,expected_train,family,hidden,seed):
 global models
 meta=c.read(folder/'model.json');assert meta['training_ids']==[rows[i]['proposition_id'] for i in expected_train]
 assert meta['training_patients']==sorted({rows[i]['subject_id'] for i in expected_train})
 assert meta['family']==family and meta['hidden']==hidden and meta['seed']==seed
 assert c.sha(folder/'weights.pt')==meta['weights_sha256']
 ss=data['s'][expected_train];xx=data['x'][expected_train][data['mask'][expected_train]]
 expected=dict(smean=ss.mean(0),sscale=np.maximum(ss.std(0),1e-4),xmean=xx.mean(0),xscale=np.maximum(xx.std(0),1e-4))
 assert all(np.allclose(v,meta['statistics'][k],atol=1e-7,rtol=1e-7) for k,v in expected.items())
 net=l.Head(family,hidden,cfg['residual_bound']);net.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));net.eval()
 models+=1
 return l.predict(net,{k:np.array(v,dtype='float32') for k,v in meta['statistics'].items()},data,ids)
cohort=[dict(rows[i],human_gt=gt[rows[i]['proposition_id']]) for i in train]
base=c.metric(cohort,[rows[i]['u2'] for i in train]);alloptions=[]
for family in cfg['families']:
 options=[]
 for hidden in cfg['hidden_sizes']:
  sums=np.zeros((len(rows),3));counts=np.zeros(len(rows),int)
  for f in folds:
   tr=np.array([i for i in train if rows[i]['subject_id'] in f['training_patients']]);va=np.array([i for i in train if rows[i]['subject_id'] in f['validation_patients']])
   for seed in cfg['training_seeds']:
    sums[va]+=replay(c.OUT/'training_001/models'/family/f'h{hidden}_f{f["fold"]}_s{seed}',va,tr,family,hidden,seed);counts[va]+=1
  assert np.all(counts[train]==3) and np.all(counts[test]==0)
  delta=sums[train]/3;old=np.load(c.OUT/'training_001'/f'{family}_h{hidden}_oof.npz')
  assert list(old['ids'])==[rows[i]['proposition_id'] for i in train]
  max_delta=max(max_delta,float(np.max(abs(delta-old['delta']))));assert np.allclose(delta,old['delta'],atol=1e-7,rtol=1e-6)
  for scale in cfg['correction_scales']:
   z=data['z'][train].copy();z[:,0]+=0 if family=='attention_no_lambda' else 2
   pred=l.decode(z+scale*delta);m=c.metric(cohort,pred)
   options.append(dict(family=family,hidden=hidden,scale=scale,meets_PA_constraint=m['PA']>=base['PA']-1e-12,metrics=m))
 eligible=[v for v in options if v['meets_PA_constraint']]
 chosen=max(eligible or options,key=lambda v:(v['metrics']['MCC'],v['metrics']['PA'],-v['metrics']['false_S'],-v['hidden'],-v['scale']))
 assert all(chosen[k]==sel[family][k] for k in chosen)
 alloptions.extend(options)
 for seed in cfg['training_seeds']:replay(c.OUT/'inference_001/models'/f'{family}_s{seed}',test,train,family,sel[family]['hidden'],seed)
assert models==135
# One fixed primary CV fit reproduces saved weights, without selection on confirmation.
family='attention';hidden=32;seed=32;f=folds[0];tr=np.array([i for i in train if rows[i]['subject_id'] in f['training_patients']])
y=np.array([c.LABELS.index(gt[r['proposition_id']]) if r['proposition_id'] in gt else -1 for r in rows])
net,stats,losses=l.fit(data,tr,y,family,hidden,seed,cfg)
saved=torch.load(c.OUT/'training_001/models/attention/h32_f0_s32/weights.pt',map_location='cpu',weights_only=True)
wd=max(float(torch.max(torch.abs(net.state_dict()[k]-v))) for k,v in saved.items())
assert wd<1e-6,wd
summary=dict(passed=True,historical_frozen_files=len(history),input_claims=len(rows),NLI_pairs_rebuilt=len(pairs),all_head_models_replayed=models,OOF_max_abs_difference=max_delta,training_options_recomputed=len(alloptions),primary_model_refit=1,refit_max_weight_difference=wd,NLI_encoder_not_rerun=True,API_calls=0)
(a/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary),flush=True)
# Full 002 evaluation replay to a new ignored directory, preserving official outputs.
dest=root/'outputs/replays/audit032_20260920';dest.mkdir(parents=True,exist_ok=False);(dest/'inference_001').mkdir()
for name in ('manifest.json','predictions_blind.jsonl'):shutil.copyfile(c.OUT/'inference_001'/name,dest/'inference_001'/name)
original=c.OUT;c.OUT=dest
import evaluate032
evaluate032.run();same=[]
for p in (original/'analysis_001').iterdir():
 if p.is_file() and p.name not in ('GT_connection.json','manifest.json'):
  assert p.read_bytes()==(dest/'analysis_001'/p.name).read_bytes(),p.name
  same.append(p.name)
(a/'replay_check.json').write_text(json.dumps(dict(passed=True,exact_evaluation_files=same,new_API_calls=0),indent=2)+'\n',encoding='utf-8')
print('Evaluation byte-equal',len(same),flush=True)
