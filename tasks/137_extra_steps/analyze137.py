"""Compare extra training against136 using exactly the same claim-repeat input."""
from pathlib import Path
import argparse,json,sys,statistics
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect,reason
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=['screen160','old500','full1817']);p.add_argument('--candidate',default='extra_steps');p.add_argument('--results',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
 P=R/'.local_models/134_author_baselines';keys={r['id']:r for r in c.rows(P/'keys.jsonl')};job=c.read(P/'job.json')
 targets=set(job['phases'][0]['ids']) if a.scope=='screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope=='old500' else set(keys))
 raw=collect(a.results);base={i:dict(valid=r['parsed']['valid'],verdict=r['parsed']['verdict'],input_tokens=r['input_tokens']) for i,r in collect([R/'.local_models/136_claim_repeat_transfer/evidence/screen160/claim_repeat',R/'.local_models/136_claim_repeat_transfer/evidence/old500/claim_repeat',R/'.local_models/136_claim_repeat_transfer/evidence/full1817/claim_repeat']).items()}
 if not targets<=raw.keys():raise ValueError('Missing first receipts')
 if not all(base[i]['valid'] for i in targets):raise ValueError('Unexpected invalid136 baseline')
 valid=sorted(i for i in targets if raw[i]['parsed']['valid']);rows=[keys[i] for i in valid]
 old={i:dict(verdict=base[i]['verdict']) for i in valid};new={i:dict(verdict=raw[i]['parsed']['verdict']) for i in valid}
 score=paired(rows,old,new,'claim_repeat136',bootstrap=a.bootstrap)
 groups=dict(all=rows,natural=[r for r in rows if r['old_panel']=='natural'],pressure=[r for r in rows if r['old_panel']=='pressure'],new1317=[r for r in rows if r['subset']=='new'],history103_180=[r for r in rows if r['history103_panel'] in ('natural','pressure')])
 panels={name:paired(rs,old,new,'claim_repeat136') for name,rs in groups.items() if rs}
 history={'paper_r1':metrics(rows,{r['id']:r['paper_r1'] for r in rows})};history_predictions={}
 for name,file,field in [('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),('label_only107',P.parent/'116_research_cycle/baseline107_selection1817.jsonl','verdict'),('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132')]:
  data={r['id']:r for r in c.rows(file)};history_predictions[name]={i:data[i][field] for i in valid};history[name]=metrics(rows,history_predictions[name])
 author={name:collect([P/'bundle/results'/name,P/'evidence'/name]) for name in ['author_base9b','author_lora9b']}
 core=[r for r in rows if all(author[n][r['id']]['parsed']['valid'] for n in author)]
 core_scores={name:metrics(core,{r['id']:data[r['id']]['parsed']['verdict'] for r in core}) for name,data in author.items()}
 core_scores.update(paper_r1=metrics(core,{r['id']:r['paper_r1'] for r in core}),claim_repeat136=metrics(core,{r['id']:old[r['id']]['verdict'] for r in core}),extra_steps=metrics(core,{r['id']:new[r['id']]['verdict'] for r in core}))
 core_scores.update({name:metrics(core,{r['id']:preds[r['id']] for r in core}) for name,preds in history_predictions.items()})
 oldm=score['scores']['claim_repeat136'];newm=score['scores']['candidate'];screen=a.scope=='screen160'
 quality=score['delta_MCC']>=(.015 if screen else .01) or (score['delta_correct']>=(3 if screen else 5) and score['delta_MCC']>=-.01)
 risk=score['delta_false_S']<=(-2 if screen else -5) and score['delta_correct']>=(-3 if screen else -5) and score['delta_MCC']>=(-.03 if screen else -.02)
 guards=dict(valid_coverage=len(valid)/len(targets)>=.95,no_large_false_S_jump=score['delta_false_S']<=(3 if screen else 5),no_major_class_collapse=all(newm['per_class'][g]['tp']>=.5*oldm['per_class'][g]['tp'] for g in LABELS if oldm['per_class'][g]['tp']>=6),no_near_zero_class=all(oldm['per_class'][g]['recall'] is None or oldm['per_class'][g]['recall']<.1 or newm['per_class'][g]['recall']>=.05 for g in LABELS))
 token_deltas=[raw[i]['input_tokens']-base[i]['input_tokens'] for i in sorted(targets)]
 input_cost=dict(mean_extra_tokens=statistics.mean(token_deltas),median_extra_tokens=statistics.median(token_deltas),max_extra_tokens=max(token_deltas),relative_total_input_increase=sum(token_deltas)/sum(base[i]['input_tokens'] for i in targets),output_token_cap=384,interpretation='Input tokens only; billed GPU wall time also includes all preparation/loading/compilation/wait/return.')
 result=dict(candidate='extra_steps',base_weights='120_final369_plus149',expected_N=len(targets),joint_valid_N=len(valid),primary=score,panels=panels,by_author={label:paired([r for r in rows if r['author']==label],old,new,'claim_repeat136') for label in sorted({r['author'] for r in rows})},historical_on_primary_IDs=history,three_baseline_common_N=len(core),three_baseline_common_scores=core_scores,coverage=dict(missing_ids=sorted(targets-raw.keys()),invalid_ids=sorted(targets-set(valid))),screening=dict(quality_signal=quality,risk_signal=risk,guards=guards,continue_signal=bool(all(guards.values()) and (quality or risk))),input_cost=input_cost,new_training=True,new_API=0)
 baseline_target_correct=sum(base[i]['verdict']==keys[i]['GT'] for i in targets)
 result['operational_coverage']=dict(target_N=len(targets),valid_N=len(valid),unanswered_N=len(targets)-len(valid),
  candidate_correct=newm['correct'],baseline_correct_full_target=baseline_target_correct,
  candidate_PA_full_target_bounds=[newm['correct']/len(targets),(newm['correct']+len(targets)-len(valid))/len(targets)],
  candidate_correct_minus_baseline_full_target=newm['correct']-baseline_target_correct,
  note='Invalid output remains unanswered; no old label is substituted. Bounds are not a new label mapping.')
 if a.scope=='full1817':
  result['screening']=dict(applicable=False,reason='Protocol expansion gates apply to160 and500 only; full1817 has no further cohort to expand.',legacy_500_conditions=result['screening'],continue_signal=None)
 a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/(a.scope+'.json'),result)
 c.putl(a.out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],claim_repeat136=old[i]['verdict'],extra_steps=new[i]['verdict']) for i in valid])
 c.putl(a.out/(a.scope+'_receipt_status_sanitized.jsonl'),[dict(id=i,valid=raw[i]['parsed']['valid'],verdict=raw[i]['parsed']['verdict'],finish_reason=raw[i]['finish_reason']) for i in sorted(targets)])
 lines=['# extra_steps：'+a.scope,'',f'目标{len(targets)}，共同有效{len(rows)}；无效不补旧答案。','','|配置|MCC|PA|正确|FS/非S|S/NS/NA召回|','|---|---:|---:|---:|---:|---|']
 for name,m in dict(score['scores'],**history).items():
  name='extra_steps' if name=='candidate' else name
  recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  lines.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{recall}|")
 lines+=['',f"ΔMCC {score['delta_MCC']:+.4f}；Δ正确{score['delta_correct']:+d}；Δfalse-S{score['delta_false_S']:+d}。",'完整混淆矩阵、类别救回/误伤、患者和作者方向以及继续门槛见JSON。','']
 (a.out/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
 print(c.canonical(dict(delta_MCC=score['delta_MCC'],delta_correct=score['delta_correct'],delta_false_S=score['delta_false_S'],screening=result['screening'])))
if __name__=='__main__':main()
