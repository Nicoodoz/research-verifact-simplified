"""Prepared CPU analyzer for one later-selected native candidate; never launches it."""
from pathlib import Path
from collections import Counter
import argparse,json,re,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c

def collect(folders):
 result={}
 for folder in folders:
  for f in Path(folder).glob('*.json'):
   row=c.read(f)
   if 'id' not in row:continue
   if row['id'] in result and result[row['id']]['content']!=row['content']:raise ValueError('Conflicting first receipt')
   result[row['id']]=row
 return result

def reason(row):
 text=row['content'];m=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',text,re.S|re.I)
 try:
  obj=json.loads(m[1] if m else text);value=obj.get('reason')
  return dict(present=isinstance(value,str) and bool(value.strip()),first_key=next(iter(obj),None))
 except (ValueError,AttributeError,TypeError):return dict(present=False,first_key=None)

def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500','full1817'],required=True)
 p.add_argument('--candidate',default='reason_first');p.add_argument('--results',type=Path,nargs='+',required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
 baseP=R/'.local_models/134_author_baselines'
 keys={r['id']:r for r in c.rows(baseP/'keys.jsonl')};job=c.read(baseP/'job.json')
 targets=set(job['phases'][0]['ids']) if a.scope=='screen160' else ({i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')} if a.scope=='old500' else set(keys))
 new=collect(a.results);base=collect([baseP/'bundle/results/author_lora9b',baseP/'evidence/author_lora9b'])
 raw_base=collect([baseP/'bundle/results/author_base9b',baseP/'evidence/author_base9b'])
 if not targets<=set(new) or not targets<=set(base):raise ValueError('Required first receipts missing; no imputation')
 candidate_invalid=sorted(i for i in targets if not new[i]['parsed']['valid'])
 baseline_invalid=sorted(i for i in targets if not base[i]['parsed']['valid'])
 valid=sorted(i for i in targets if new[i]['parsed']['valid'] and base[i]['parsed']['valid']);rows=[keys[i] for i in valid]
 old={i:dict(verdict=base[i]['parsed']['verdict']) for i in valid};cand={i:dict(verdict=new[i]['parsed']['verdict']) for i in valid}
 score=paired(rows,old,cand,'author_lora9b',bootstrap=a.bootstrap)
 groups={'all':rows,'natural':[r for r in rows if r['old_panel']=='natural'],'pressure':[r for r in rows if r['old_panel']=='pressure'],'new1317':[r for r in rows if r['subset']=='new'],
  'history103_180':[r for r in rows if r['history103_panel'] in ('natural','pressure')]}
 panels={name:paired(rs,old,cand,'author_lora9b') for name,rs in groups.items() if rs}
 history={}
 sources=[('label_only107',baseP.parent/'116_research_cycle/baseline107_selection1817.jsonl','verdict'),
          ('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),
          ('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132')]
 for name,path,field in sources:
  data={r['id']:r for r in c.rows(path)};history[name]=metrics(rows,{i:data[i][field] for i in valid})
 history['paper_r1']=metrics(rows,{r['id']:r['paper_r1'] for r in rows})
 core=[r for r in rows if raw_base[r['id']]['parsed']['valid']]
 core_scores={'author_base9b':metrics(core,{r['id']:raw_base[r['id']]['parsed']['verdict'] for r in core}),
  'author_lora9b':metrics(core,{r['id']:old[r['id']]['verdict'] for r in core}),a.candidate:metrics(core,{r['id']:cand[r['id']]['verdict'] for r in core}),
  'paper_r1':metrics(core,{r['id']:r['paper_r1'] for r in core})}
 by_author={label:paired([r for r in rows if r['author']==label],old,cand,'author_lora9b') for label in sorted({r['author'] for r in rows})}
 missing_reason=[i for i in valid if not reason(new[i])['present']]
 quality=score['delta_MCC']>=.015 or (score['delta_correct']>=3 and score['delta_MCC']>=-.01)
 risk=score['delta_false_S']<=-2 and score['delta_correct']>=-3 and score['delta_MCC']>=-.03
 oldm=score['scores']['author_lora9b'];newm=score['scores']['candidate']
 guards=dict(valid_coverage=len(valid)/len(targets)>=.95,no_near_zero_class=all(newm['per_class'][g]['recall'] is None or oldm['per_class'][g]['recall'] is None or oldm['per_class'][g]['recall']<.1 or newm['per_class'][g]['recall']>=.05 for g in LABELS),
  no_major_class_collapse=all(newm['per_class'][g]['tp']>=.5*oldm['per_class'][g]['tp'] for g in LABELS if oldm['per_class'][g]['tp']>=6),
  no_large_false_S_jump=score['delta_false_S']<=3)
 if a.scope!='screen160':
  quality=score['delta_MCC']>=.01 or (score['delta_correct']>=5 and score['delta_MCC']>=-.01)
  risk=score['delta_false_S']<=-5 and score['delta_correct']>=-5 and score['delta_MCC']>=-.02
  guards['no_large_false_S_jump']=score['delta_false_S']<=5
 own_scores={}
 for name,data in [('author_lora9b',base),(a.candidate,new)]:
  own=[keys[i] for i in sorted(targets) if data[i]['parsed']['valid']]
  m=metrics(own,{r['id']:data[r['id']]['parsed']['verdict'] for r in own})
  m['PA_full_target_bounds']=[m['correct']/len(targets),(m['correct']+len(targets)-len(own))/len(targets)]
  own_scores[name]=m
 missing_own=[i for i in targets if new[i]['parsed']['valid'] and not reason(new[i])['present']]
 result=dict(candidate=a.candidate,scope=a.scope,expected_N=len(targets),joint_valid_N=len(valid),standalone_scores=own_scores,
  coverage=dict(candidate_invalid_ids=candidate_invalid,baseline_invalid_ids=baseline_invalid,
   candidate_invalid_by_GT=dict(Counter(keys[i]['GT'] for i in candidate_invalid))),primary=score,panels=panels,
  historical_on_primary_IDs=history,three_baseline_common_N=len(core),three_baseline_common_scores=core_scores,by_author=by_author,
  reason=dict(missing_on_joint_valid_N=len(missing_reason),missing_on_all_candidate_valid_N=len(missing_own),missing_valid_ids=sorted(missing_own),
   first_key_counts=dict(Counter(reason(new[i])['first_key'] for i in valid))),
  screening=dict(quality_signal=quality,risk_signal=risk,guards=guards,continue_signal=bool(all(guards.values()) and (quality or risk))),
  no_label_rewrite=True,no_evaluation_training=True)
 a.out.mkdir(parents=True,exist_ok=True);c.put(a.out/(a.scope+'.json'),result)
 c.putl(a.out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],candidate=cand[i]['verdict'],author_lora9b=old[i]['verdict']) for i in valid])
 c.putl(a.out/(a.scope+'_receipt_status_sanitized.jsonl'),[dict(id=i,GT=keys[i]['GT'],**{name:dict(valid=data[i]['parsed']['valid'],verdict=data[i]['parsed']['verdict'],finish_reason=data[i]['finish_reason'],reason_present=reason(data[i])['present']) for name,data in [('author_lora9b',base),(a.candidate,new)]}) for i in sorted(targets)])
 lines=[f'# {a.candidate}：{a.scope}','',f'计划{len(targets)}；主比较共同有效{len(valid)}。无效不填旧答案。',
  '','|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 models=dict(score['scores'],**history)
 for name,m in models.items():
  name=a.candidate if name=='candidate' else name
  recalls='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  lines.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recalls}|")
 lines+=['','逐类救回／误伤、患者及作者方向、混淆矩阵、缺reason与首字段顺序见JSON。主比较只改变原生输入／生成前缀，不改模型标签。',
  '初筛继续信号：'+str(result['screening'])+'。该信号需结合真实类别损失和剩余预算解释；不把短样本结果外推成整条路线结论。','']
 (a.out/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
 print(c.canonical(dict(candidate=a.candidate,scope=a.scope,joint_valid=len(valid),delta_MCC=score['delta_MCC'],delta_correct=score['delta_correct'],delta_false_S=score['delta_false_S'],screening=result['screening'])))

if __name__=='__main__':main()
