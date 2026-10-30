"""Compare the unchanged claim-repeat method against actual120 cached predictions."""
from pathlib import Path
import argparse,json,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect,reason
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=['screen160','old500','full1817']);p.add_argument('--candidate',default='claim_repeat');p.add_argument('--results',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
 P=R/'.local_models/134_author_baselines';keys={r['id']:r for r in c.rows(P/'keys.jsonl')};job=c.read(P/'job.json')
 targets=set(job['phases'][0]['ids']) if a.scope=='screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope=='old500' else set(keys))
 raw=collect(a.results);base={r['id']:r for r in c.rows(R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')}
 if not targets<=raw.keys():raise ValueError('Missing first receipts')
 if not all(base[i]['valid'] for i in targets):raise ValueError('Unexpected invalid120 baseline')
 valid=sorted(i for i in targets if raw[i]['parsed']['valid']);rows=[keys[i] for i in valid]
 old={i:dict(verdict=base[i]['verdict']) for i in valid};new={i:dict(verdict=raw[i]['parsed']['verdict']) for i in valid}
 score=paired(rows,old,new,'full_pool120',bootstrap=a.bootstrap)
 groups=dict(all=rows,natural=[r for r in rows if r['old_panel']=='natural'],pressure=[r for r in rows if r['old_panel']=='pressure'],new1317=[r for r in rows if r['subset']=='new'],history103_180=[r for r in rows if r['history103_panel'] in ('natural','pressure')])
 panels={name:paired(rs,old,new,'full_pool120') for name,rs in groups.items() if rs}
 history={'paper_r1':metrics(rows,{r['id']:r['paper_r1'] for r in rows})}
 for name,file,field in [('label_only107',P.parent/'116_research_cycle/baseline107_selection1817.jsonl','verdict'),('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132')]:
  data={r['id']:r for r in c.rows(file)};history[name]=metrics(rows,{i:data[i][field] for i in valid})
 author={name:collect([P/'bundle/results'/name,P/'evidence'/name]) for name in ['author_base9b','author_lora9b']}
 core=[r for r in rows if all(author[n][r['id']]['parsed']['valid'] for n in author)]
 core_scores={name:metrics(core,{r['id']:data[r['id']]['parsed']['verdict'] for r in core}) for name,data in author.items()}
 core_scores.update(paper_r1=metrics(core,{r['id']:r['paper_r1'] for r in core}),full_pool120=metrics(core,{r['id']:old[r['id']]['verdict'] for r in core}),claim_repeat=metrics(core,{r['id']:new[r['id']]['verdict'] for r in core}))
 oldm=score['scores']['full_pool120'];newm=score['scores']['candidate'];screen=a.scope=='screen160'
 quality=score['delta_MCC']>=(.015 if screen else .01) or (score['delta_correct']>=(3 if screen else 5) and score['delta_MCC']>=-.01)
 risk=score['delta_false_S']<=(-2 if screen else -5) and score['delta_correct']>=(-3 if screen else -5) and score['delta_MCC']>=(-.03 if screen else -.02)
 guards=dict(valid_coverage=len(valid)/len(targets)>=.95,no_large_false_S_jump=score['delta_false_S']<=(3 if screen else 5),no_major_class_collapse=all(newm['per_class'][g]['tp']>=.5*oldm['per_class'][g]['tp'] for g in LABELS if oldm['per_class'][g]['tp']>=6),no_near_zero_class=all(oldm['per_class'][g]['recall'] is None or oldm['per_class'][g]['recall']<.1 or newm['per_class'][g]['recall']>=.05 for g in LABELS))
 result=dict(candidate='claim_repeat',base_weights='120_final369',expected_N=len(targets),joint_valid_N=len(valid),primary=score,panels=panels,by_author={label:paired([r for r in rows if r['author']==label],old,new,'full_pool120') for label in sorted({r['author'] for r in rows})},historical_on_primary_IDs=history,three_baseline_common_N=len(core),three_baseline_common_scores=core_scores,coverage=dict(missing_ids=sorted(targets-raw.keys()),invalid_ids=sorted(targets-set(valid))),screening=dict(quality_signal=quality,risk_signal=risk,guards=guards,continue_signal=bool(all(guards.values()) and (quality or risk))),new_training=False,new_API=0)
 a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/(a.scope+'.json'),result)
 c.putl(a.out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],full_pool120=old[i]['verdict'],claim_repeat=new[i]['verdict']) for i in valid])
 c.putl(a.out/(a.scope+'_receipt_status_sanitized.jsonl'),[dict(id=i,valid=raw[i]['parsed']['valid'],verdict=raw[i]['parsed']['verdict'],finish_reason=raw[i]['finish_reason']) for i in sorted(targets)])
 lines=['# claim_repeat迁移到120：'+a.scope,'',f'目标{len(targets)}，共同有效{len(rows)}；无效不补旧答案。','','|配置|MCC|PA|正确|FS/非S|S/NS/NA召回|','|---|---:|---:|---:|---:|---|']
 for name,m in dict(score['scores'],**history).items():
  recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  lines.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{recall}|")
 lines+=['',f"ΔMCC {score['delta_MCC']:+.4f}；Δ正确{score['delta_correct']:+d}；Δfalse-S{score['delta_false_S']:+d}。",'完整混淆矩阵、类别救回/误伤、患者和作者方向以及继续门槛见JSON。','']
 (a.out/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
 print(c.canonical(dict(delta_MCC=score['delta_MCC'],delta_correct=score['delta_correct'],delta_false_S=score['delta_false_S'],screening=result['screening'])))
if __name__=='__main__':main()
