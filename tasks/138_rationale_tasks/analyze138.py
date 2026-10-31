"""Score actual138 first outputs against cached136 and matched replay when present."""
from pathlib import Path
import argparse,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
P=R/'.local_models/138_rationale_tasks'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['rationale_tasks','label_replay'],required=True);ap.add_argument('--scope',choices=['screen160','old500','full1817'],default='screen160');ap.add_argument('--results',type=Path,nargs='+');ap.add_argument('--bootstrap',action='store_true');args=ap.parse_args()
 done=c.read(P/args.arm/'evidence/training_done.json');assert (done['steps'],done['consumed'])==(48,384)
 K=R/'.local_models/134_author_baselines';keys={r['id']:r for r in c.rows(K/'keys.jsonl')}
 target=set(c.read(K/'job.json')['phases'][0]['ids']) if args.scope=='screen160' else {i for i,r in keys.items() if args.scope=='full1817' or r['old_panel'] in ('natural','pressure')}
 paths=args.results or [P/args.arm/'evidence/predictions',P/args.arm/'evidence/old500',P/args.arm/'evidence/full1817',*[P/'extension'/args.arm/scope/'evidence'/args.arm for scope in ['old500','full1817']]]
 raw=collect(paths);baseline=collect([R/'.local_models/136_claim_repeat_transfer/evidence'/scope/'claim_repeat' for scope in ['screen160','old500','full1817']])
 for i in target&raw.keys():
  assert raw[i]['adapter_sha256']==done['adapter_sha256'] and raw[i]['arm']==args.arm
  assert raw[i]['prompt_token_sha256']==baseline[i]['prompt_token_sha256']
 valid=sorted(i for i in target&raw.keys() if raw[i]['parsed']['valid']);rs=[keys[i] for i in valid]
 if not rs:raise ValueError('No valid actual candidate response')
 old={i:{'verdict':baseline[i]['parsed']['verdict']} for i in valid};new={i:{'verdict':raw[i]['parsed']['verdict']} for i in valid}
 p=paired(rs,old,new,'claim_repeat136',bootstrap=args.bootstrap)
 panels={name:paired(group,old,new,'claim_repeat136') for name,group in dict(natural=[r for r in rs if r['old_panel']=='natural'],pressure=[r for r in rs if r['old_panel']=='pressure'],new1317=[r for r in rs if r['subset']=='new'],history103_180=[r for r in rs if r['history103_panel'] in ('natural','pressure')]).items() if group}
 history={'paper_r1':metrics(rs,{r['id']:r['paper_r1'] for r in rs})}
 for name,path,field in [('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl','verdict'),('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132'),('extra_steps137',R/'outputs/137_extra_steps/full1817_predictions_sanitized.jsonl','extra_steps')]:
  lookup={r['id']:r[field] for r in c.rows(path)};history[name]=metrics(rs,lookup)
 author={name:collect([K/'bundle/results'/name,K/'evidence'/name]) for name in ['author_base9b','author_lora9b']}
 core=[r for r in rs if all(author[name][r['id']]['parsed']['valid'] for name in author)]
 core_scores={name:metrics(core,{r['id']:author[name][r['id']]['parsed']['verdict'] for r in core}) for name in author}
 core_scores.update(paper_r1=metrics(core,{r['id']:r['paper_r1'] for r in core}),claim_repeat136=metrics(core,{r['id']:old[r['id']]['verdict'] for r in core}))
 core_scores[args.arm]=metrics(core,{r['id']:new[r['id']]['verdict'] for r in core})
 base104={r['id']:r for r in c.rows(R/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r['arm']=='base_judge'}
 overlap=[r for r in rs if r['id'] in base104 and base104[r['id']]['parsed']['valid']]
 base_comparison=dict(N=len(overlap),scores={})
 if overlap:
  base_comparison['scores']=dict(base104_9b=metrics(overlap,{r['id']:base104[r['id']]['parsed']['verdict'] for r in overlap}),claim_repeat136=metrics(overlap,{r['id']:old[r['id']]['verdict'] for r in overlap}))
  base_comparison['scores'][args.arm]=metrics(overlap,{r['id']:new[r['id']]['verdict'] for r in overlap})
  for name,path,field in [('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl','verdict')]:
   lookup={r['id']:r[field] for r in c.rows(path)};base_comparison['scores'][name]=metrics(overlap,lookup)
  base_comparison['scores']['paper_r1']=metrics(overlap,{r['id']:r['paper_r1'] for r in overlap})
 m0=p['scores']['claim_repeat136'];m1=p['scores']['candidate'];small=args.scope=='screen160'
 quality=p['delta_MCC']>=(.015 if small else .01) or (p['delta_correct']>=(3 if small else 5) and p['delta_MCC']>=-.01)
 risk=p['delta_false_S']<=(-2 if small else -5) and p['delta_correct']>=(-3 if small else -5) and p['delta_MCC']>=(-.03 if small else -.02)
 guards=dict(complete_coverage=target<=raw.keys(),valid_coverage=len(rs)/len(target)>=.95,false_S_increase=p['delta_false_S']<=(3 if small else 5),no_major_class_loss=all(m1['per_class'][g]['tp']>=.5*m0['per_class'][g]['tp'] for g in LABELS if m0['per_class'][g]['tp']>=6))
 result=dict(arm=args.arm,scope=args.scope,expected_N=len(target),valid_N=len(rs),coverage=dict(missing_ids=sorted(target-raw.keys()),invalid_ids=sorted((target&raw.keys())-set(valid))),primary=p,panels=panels,by_author={a:paired([r for r in rs if r['author']==a],old,new,'claim_repeat136') for a in sorted({r['author'] for r in rs})},historical_on_same_IDs=history,three_baseline_common_N=len(core),three_baseline_common_scores=core_scores,screening=dict(quality_signal=quality,risk_signal=risk,guards=guards,continue_signal=all(guards.values()) and (quality or risk)))
 other='label_replay' if args.arm=='rationale_tasks' else 'rationale_tasks'
 result['same_prompt_unfinetuned_overlap']=base_comparison
 other_raw=collect([P/other/'evidence/predictions',P/other/'evidence/old500',P/other/'evidence/full1817',*[P/'extension'/other/scope/'evidence'/other for scope in ['old500','full1817']]])
 if other_raw:
  other_done=c.read(P/other/'evidence/training_done.json');assert (other_done['steps'],other_done['consumed'])==(48,384)
  for i in target&other_raw.keys():
   assert other_raw[i]['arm']==other and other_raw[i]['adapter_sha256']==other_done['adapter_sha256']
   assert other_raw[i]['prompt_token_sha256']==baseline[i]['prompt_token_sha256']
 joint=sorted(i for i in valid if i in other_raw and other_raw[i]['parsed']['valid'])
 if joint:
  cand=raw if args.arm=='rationale_tasks' else other_raw;control=other_raw if args.arm=='rationale_tasks' else raw
  result['rationale_vs_replay']=paired([keys[i] for i in joint],{i:{'verdict':control[i]['parsed']['verdict']} for i in joint},{i:{'verdict':cand[i]['parsed']['verdict']} for i in joint},'label_replay',bootstrap=args.bootstrap)
 O=R/'outputs/138_rationale_tasks';c.put(O/(args.arm+'_'+args.scope+'.json'),result)
 c.putl(O/(args.arm+'_'+args.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],prediction=new[i]['verdict']) for i in valid])
 c.putl(O/(args.arm+'_'+args.scope+'_receipt_status_sanitized.jsonl'),[dict(id=i,received=i in raw,valid=i in valid,verdict=raw[i]['parsed']['verdict'] if i in raw else None) for i in sorted(target)])
 print(c.canonical(dict(arm=args.arm,N=len(rs),delta_MCC=p['delta_MCC'],delta_correct=p['delta_correct'],delta_false_S=p['delta_false_S'],screening=result['screening'])))
if __name__=='__main__':main()
