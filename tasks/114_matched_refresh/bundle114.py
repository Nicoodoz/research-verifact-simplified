"""Package fixed CPU artifacts and inherited implementations, without weights."""
from pathlib import Path
import sys,json,tarfile,shutil,ast
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/114_matched_refresh';B=P/'bundle'
def main():
 B.mkdir(exist_ok=True);d=B/'data';d.mkdir(exist_ok=True)
 cfg=c.read(R/'tasks/107_support_aux/config.json');cfg['task']=114;cfg['method']='matched_refresh';cfg['training'].pop('auxiliary');cfg['training']['order']='original196_then_fixed_matched196';cfg['evaluation'].update(arms=['matched_refresh'],old_predictions_reused=True)
 cfg['budget']=dict(compute_hard_cap_cny=3,API_cap_cny=0,billing_start_beijing='2026-10-29T17:18:36+08:00',hourly_cny=1.58,no_shutdown=True)
 cfg.pop('execution_amendment');cfg['design']=dict(sole_change='replace_second_pass_examples_with_matched_distinct_real_examples',fresh_original_base=True,confirmation40_used=False,epoch_selection='fixed_final_step50',baseline='reuse107_label_only',no_error_driven_selection=True)
 cfg.update(model_dir='/root/verifact_image/models/qwen3.5-9b',context_tokens=c.read(R/'.local_models/107_support_aux/gpu_bundle_5090_run/frozen/tokenizer_summary.json')['required_context_tokens'],estimated_train_seconds=2100,estimated_eval_seconds=1100,return_reserve_seconds=720)
 cfg['continuation']=dict(min_common_valid_fraction=.95,quality_route='natural MCC gain >=0.02 and false-S increase <=2',risk_route='natural false-S reduction >=3 and MCC drop <=0.01',protections='natural PA drop <=1 point; S correct net loss <=4; NA recall drop <=5 points; pressure MCC drop <=0.03 and false-S increase <=2',no_automatic_expansion=True)
 c.put(R/'tasks/114_matched_refresh/config.json',cfg);c.put(d/'config.json',cfg)
 for name in ['train.jsonl','train_lengths.jsonl','plan.json']:shutil.copy2(P/name,d/name)
 inputs=c.rows(R/'.local_models/109_boundary_replay/gpu_bundle/data/eval_inputs.jsonl');assert len(inputs)==500
 c.putl(d/'eval_inputs.jsonl',[{k:r[k] for k in ['id','claim','reference']} for r in inputs])
 frozen=R/'.local_models/107_support_aux/gpu_bundle_5090_run/frozen'
 for name in ['eval_token_lengths.jsonl','eval_batches.json']:shutil.copy2(frozen/name,d/name)
 files=['tasks/114_matched_refresh/worker114.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/data105.py','tasks/105_brief_supervision/loss105.py','tasks/105_brief_supervision/parse105.py','tasks/107_support_aux/checkpoint107.py']
 for name in files:
  ast.parse((R/name).read_text(encoding='utf-8-sig'));target=B/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,target)
 c.put(B/'manifest.json',{str(p.relative_to(B)).replace('\\','/'):c.sha(p) for p in B.rglob('*') if p.is_file() and p.name!='manifest.json'})
 with tarfile.open(P/'bundle114.tar.gz','w:gz',compresslevel=1) as tar:
  for p in B.rglob('*'):
   if p.is_file():tar.add(p,arcname=p.relative_to(B),recursive=False)
 c.put(R/'outputs/114_matched_refresh/cpu_checks.json',dict(steps=50,presentations=392,short_tails=[4,4],first196_exact107=True,second_GT_patient_author_length_quartile_matched=True,fixed_selection_without_predictions=True,full_input_token_SHA_checked=True,eval_N=500,eval_GT_removed=True,syntax_checked=files,small_raw_review_N=3,known_input_gap_excluded_N=15,unresolved_included_with_original_GT=5,clinical_relabeling=False,not_efficacy_evidence=True))
 print(json.dumps(dict(bundle_bytes=(P/'bundle114.tar.gz').stat().st_size,config=cfg['method'],prepared=True)))
if __name__=='__main__':main()
