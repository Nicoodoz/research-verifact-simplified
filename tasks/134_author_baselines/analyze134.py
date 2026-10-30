"""CPU comparison of committed native responses; never rewrites their labels."""
from pathlib import Path
from collections import Counter
import argparse,json,re,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/134_author_baselines';O=R/'outputs/134_author_baselines'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS

def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500','full1817'],required=True);p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
 keys={r['id']:r for r in c.rows(P/'keys.jsonl')};job=c.read(P/'job.json')
 if a.scope=='screen160':target=set(job['phases'][0]['ids'])
 elif a.scope=='old500':target={i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')}
 else:target=set(keys)
 receipts={};coverage={}
 for arm in job['arms']:
  receipts[arm]={}
  for folder in [P/'bundle/results'/arm,P/'evidence'/arm]:
   for f in folder.glob('*.json'):
    r=c.read(f);i=r['id']
    content=r['content'];fence=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',content,re.S|re.I)
    try:reason=json.loads(fence[1] if fence else content).get('reason')
    except (ValueError,TypeError,AttributeError):reason=None
    r['reason_is_nonempty_string']=isinstance(reason,str) and bool(reason.strip())
    if i in receipts[arm] and receipts[arm][i]['content']!=r['content']:raise ValueError('Conflicting first receipt')
    receipts[arm][i]=r
  received=set(receipts[arm])&target;invalid={i for i in received if not receipts[arm][i]['parsed']['valid']}
  coverage[arm]=dict(expected=len(target),received=len(received),valid=len(received-invalid),missing_ids=sorted(target-received),invalid_ids=sorted(invalid),
      missing_reason_ids=sorted(i for i in received if not receipts[arm][i]['parsed'].get('reason_present')),
      missing_reason_valid_ids=sorted(i for i in received-invalid if not receipts[arm][i]['reason_is_nonempty_string']),
      invalid_by_GT=dict(Counter(keys[i]['GT'] for i in invalid)))
 c.put(O/(a.scope+'_coverage.json'),coverage)
 if any(v['missing_ids'] for v in coverage.values()):
  print(c.canonical(dict(scope=a.scope,incomplete=True,counts={k:v['received'] for k,v in coverage.items()})));return
 valid=sorted(i for i in target if all(receipts[arm][i]['parsed']['valid'] for arm in job['arms']))
 rows=[keys[i] for i in valid]
 preds={arm:{i:dict(verdict=receipts[arm][i]['parsed']['verdict']) for i in valid} for arm in job['arms']}
 preds['paper_r1']={i:dict(verdict=keys[i]['paper_r1']) for i in valid}
 for name,path,field in [('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl','verdict'),
                         ('full_pool120',R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl','verdict'),
                         ('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132')]:
  source={r['id']:r for r in c.rows(path)};preds[name]={i:dict(verdict=source[i][field]) for i in valid}
 groups={'all':rows,'natural400':[r for r in rows if r['old_panel']=='natural'],'pressure100':[r for r in rows if r['old_panel']=='pressure'],
         'new1317':[r for r in rows if r['subset']=='new'],'history103_180':[r for r in rows if r['history103_panel'] in ('natural','pressure')]}
 standalone={}
 for arm in job['arms']:
  own=[keys[i] for i in sorted(target) if receipts[arm][i]['parsed']['valid']]
  m=metrics(own,{r['id']:receipts[arm][r['id']]['parsed']['verdict'] for r in own})
  m['PA_full_target_bounds']=[m['correct']/len(target),(m['correct']+len(target)-len(own))/len(target)]
  standalone[arm]=m
 if a.scope=='full1817':
  standalone['paper_r1']=c.read(R/'outputs/132_midpoint_update/selection1817.json')['panels']['all']['scores']['paper_r1']
 else:standalone['paper_r1']=metrics([keys[i] for i in target],{i:keys[i]['paper_r1'] for i in target})
 result=dict(scope=a.scope,coverage=coverage,standalone_scores=standalone,common_valid_N=len(rows),expected_N=len(target),panels={},by_author={},new_training=False,new_API=0)
 for name,rs in groups.items():
  if not rs:continue
  score={arm:metrics(rs,{r['id']:v[r['id']]['verdict'] for r in rs}) for arm,v in preds.items()}
  if a.scope=='full1817' and name=='history103_180':
   historical={r['id']:r for r in c.rows(R/'outputs/103_lora_selection/final_paired_predictions.jsonl')}
   if any(not historical[r['id']]['arms']['nine_native']['valid'] for r in rs):raise ValueError('Unexpected invalid historical103 row')
   score['base9b_thinking103_history']=metrics(rs,{r['id']:historical[r['id']]['predictions']['nine_native'] for r in rs})
   result['historical103_note']='Separate180 subset only: same upstream template but thinking4096 plus final768 with historical forced-thinking-stop behavior; never merged into the no-thinking baseline or attributed as a pure training effect.'
  pairs={}
  for arm,reference in [('author_lora9b','author_base9b'),('author_lora9b','full_pool120'),('author_lora9b','label_only107'),('author_base9b','paper_r1')]:
   pairs[arm+'_vs_'+reference]=paired(rs,preds[reference],preds[arm],reference,bootstrap=a.bootstrap and name=='all')
  result['panels'][name]=dict(N=len(rs),scores=score,comparisons=pairs)
 for author in sorted({r['author'] for r in rows}):
  rs=[r for r in rows if r['author']==author]
  result['by_author'][author]=dict(N=len(rs),author_lora_vs_base=paired(rs,preds['author_base9b'],preds['author_lora9b'],'author_base9b'),
    author_lora_vs120=paired(rs,preds['full_pool120'],preds['author_lora9b'],'full_pool120'))
 c.put(O/(a.scope+'.json'),result)
 c.putl(O/(a.scope+'_receipt_status_sanitized.jsonl'),[
  dict(id=i,**{arm:dict(valid=receipts[arm][i]['parsed']['valid'],verdict=receipts[arm][i]['parsed']['verdict'],finish_reason=receipts[arm][i]['finish_reason'],reason_present=receipts[arm][i]['reason_is_nonempty_string']) for arm in job['arms']}) for i in sorted(target)])
 c.putl(O/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],**{arm:v[i]['verdict'] for arm,v in preds.items()}) for i in valid])
 lines=['# 134 '+a.scope+'：统一原作者提示词比较','',f'计划{len(target)}条，共同有效{len(rows)}条。无效、缺失和reason缺失单列于coverage；不填旧答案。',
  '','## 各自有效覆盖（跨行分母可能不同，不直接作差）','','|配置|有效N|MCC|PA|正确|false-S/非S|Macro-F1|','|---|---:|---:|---:|---:|---:|---:|']
 for arm,m in standalone.items():lines.append(f"|{arm}|{m['n']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|")
 lines+=['','## 严格共同有效ID比较','','|范围／配置|N|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---:|---|']
 for group,data in result['panels'].items():
  for arm,m in data['scores'].items():
   recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{100*m['per_class'][g]['recall']:.2f}%" for g in LABELS)
   lines.append(f"|{group}/{arm}|{data['N']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recall}|")
 lines+=['','|范围／比较|ΔMCC|Δ正确|Δfalse-S|S救回/误伤|NS救回/误伤|NA救回/误伤|','|---|---:|---:|---:|---:|---:|---:|']
 for group,data in result['panels'].items():
  for label,v in data['comparisons'].items():
   classes='|'.join(f"{v['changes']['by_class'][g]['rescued']}/{v['changes']['by_class'][g]['harmed']}" for g in LABELS)
   lines.append(f"|{group}/{label}|{v['delta_MCC']:+.4f}|{v['delta_correct']:+d}|{v['delta_false_S']:+d}|{classes}|")
 lines+=['','## 共同有效集合的混淆矩阵','','每格依次为预测S／NS／NA的数量。','','|配置|真实S|真实NS|真实NA|','|---|---|---|---|']
 for arm,m in result['panels']['all']['scores'].items():
  matrix='|'.join('/'.join(str(x) for x in row) for row in m['confusion_matrix'])
  lines.append(f'|{arm}|{matrix}|')
 lines+=['','author_base9b与author_lora9b仅差120适配器；paper_r1为不同模型的作者历史系统。107/120/132使用104提示和384输出上限，属于完整方案对照。全体为已有研究暴露的开发患者。',
  '完整三分类precision/recall/F1、混淆矩阵、患者方向及作者来源分解见同名JSON；reason来自同次生成，未用旧理由替换或修正标签。','']
 (O/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
 print(c.canonical(dict(scope=a.scope,valid=len(rows),scores={k:{x:m[x] for x in ['mcc','correct','false_S','non_S']} for k,m in result['panels']['all']['scores'].items()})))

if __name__=='__main__':main()
