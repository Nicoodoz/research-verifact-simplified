"""Render138 only from actual returned48-step checkpoints and first predictions."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
R=Path(__file__).resolve().parents[2];P=R/'.local_models/138_rationale_tasks';O=R/'outputs/138_rationale_tasks';LABELS=['Supported','Not Supported','Not Addressed']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def table(scores,arm):
 out=['|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for name,m in scores.items():
  if name=='candidate':name=arm
  recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  out.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recall}|")
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['rationale_tasks','label_replay'],required=True);ap.add_argument('--scope',choices=['screen160','old500','full1817'],default='screen160');ap.add_argument('--decision',required=True);a=ap.parse_args()
 v=read(O/(a.arm+'_'+a.scope+'.json'));d=read(P/a.arm/'evidence/training_done.json');assert (d['steps'],d['consumed'])==(48,384)
 cp=P/a.arm/'evidence/train';returned=(cp/'resume.json').exists() and (P/a.arm/'transfer_complete.json').exists()
 if returned:
  pointer=read(cp/'resume.json');assert pointer['step']==48
  returned=(cp/pointer['slot']/'training_state.pt').exists() and (cp/pointer['slot']/'training_state.pt').stat().st_size>300_000_000
 if not returned:
  live=read(P/a.arm/'live_snapshot.json');pointer=live['results/train/resume.json']
  assert pointer['step']==48 and live['results/training_done.json']['adapter_sha256']==d['adapter_sha256']
 s=v['primary'];lines=['# 138 '+a.arm+'：'+a.scope,'',a.decision,'',f"已完成固定48步/384次呈现；目标{v['expected_N']}，实际有效{v['valid_N']}。本表与136使用相同输入，变化来自训练。",'',
 '## 同ID比较','']+table(s['scores']|v['historical_on_same_IDs'],a.arm)
 lines+=['','监督差别：107为原196条标签、两轮50步；120为2945条训练标签的一轮369步。132是107与120的固定有效权重中点，136只改变120的评价输入，137从120追加149步。138从120重新建立Adam，使用156个原始训练ID的192个任务位置、两轮384次呈现、48步；主臂含36个独立理由位置，对照这些位置仍预测原标签。paper_r1为作者不同模型/系统的历史发布结果，不是本轮同模型重跑。','']
 lines+=['',f"## 三个指定基线共同{v['three_baseline_common_N']}条",'']+table(v['three_baseline_common_scores'],a.arm)
 if v.get('same_prompt_unfinetuned_overlap',{}).get('N'):
  comparison=v['same_prompt_unfinetuned_overlap']
  lines+=['',f"## 104未微调9B的实际有效重合{comparison['N']}条",'']+table(comparison['scores'],a.arm)
 lines+=['','两个作者提示9B使用768输出上限；136、本候选和107/120/132/137采用104体系及384上限，136/本候选带相同claim_repeat。paper_r1是不同模型/系统历史结果，不能跨表直接相减。','',
 '## 类别、来源与面板得失','','|GT|救回|误伤|净正确|','|---|---:|---:|---:|']
 for label,x in s['changes']['by_class'].items():lines.append(f"|{label}|{x['rescued']}|{x['harmed']}|{x['rescued']-x['harmed']:+d}|")
 lines+=['',f"false-S新增{s['changes']['false_S_new']}、避免{s['changes']['false_S_avoided']}。",'', '|面板|N|ΔMCC|Δ正确|Δfalse-S|','|---|---:|---:|---:|---:|']
 for name,x in v['panels'].items():lines.append(f"|{name}|{x['N']}|{x['delta_MCC']:+.4f}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
 lines.append('')
 for name,x in v['by_author'].items():lines.append(f"- {name}：正确{x['delta_correct']:+d}，false-S{x['delta_false_S']:+d}。")
 pts=s['patient_directions'];up=sum(x['correct_delta']>0 for x in pts);down=sum(x['correct_delta']<0 for x in pts);lines+=['',f'患者正确数：{up}升/{down}降/{len(pts)-up-down}持平。','']
 for name,m in s['scores'].items():
  if name=='paper_r1':continue
  lines+=['|类别|Precision|Recall|F1|','|---|---:|---:|---:|']
  for label in LABELS:
   row=m['per_class'][label]
   values=['—' if row[k] is None else f"{row[k]:.4f}" for k in ['precision','recall','f1']]
   lines.append('|'+label+'|'+'|'.join(values)+'|')
  lines.append('')
  lines += [name+'混淆矩阵（行GT、列预测；S/NS/NA）','','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
  for g,row in zip(['S','NS','NA'],m['confusion_matrix']):lines.append('|'+g+'|'+'|'.join(map(str,row))+'|')
  lines.append('')
 if 'patient_bootstrap' in s:
  lo,hi=s['patient_bootstrap']['metrics']['mcc']['ci95'];lines += [f'1000次患者配对ΔMCC 95%区间[{lo:+.4f},{hi:+.4f}]；不涵盖训练随机性、历史选型或新医院泛化。','']
 if a.arm=='rationale_tasks' and a.scope=='screen160' and (P/'historical_overlap.json').exists():
  h=read(P/'historical_overlap.json');ns=next(x for x in h['classes'] if x['GT']=='Not Supported')
  lines += [f"描述性检查：160条中{h['same_as137']}条与历史137同标签，本次救回的{ns['new_rescued']}条NS中有{ns['same_rescues_in137']}条也曾被137救回。137不是匹配48步对照，这种重合不能证明或排除理由任务作用。",'']
 if 'rationale_vs_replay' in v:
  x=v['rationale_vs_replay'];lines+=['## 与匹配标签回放的直接比较','']+table(x['scores'],'rationale_tasks')+[f"ΔMCC{x['delta_MCC']:+.4f}，Δ正确{x['delta_correct']:+d}，Δfalse-S{x['delta_false_S']:+d}。",'']
  if 'patient_bootstrap' in x:
   lo,hi=x['patient_bootstrap']['metrics']['mcc']['ci95'];lines += [f'患者配对ΔMCC 95%区间[{lo:+.4f},{hi:+.4f}]；该区间不覆盖重新训练和历史选型的不确定性。','']
 else:lines+=['匹配标签回放对照尚无此范围的完整结果；此时不能把相对136的变化全部归因于理由任务。','']
 session=read(P/a.arm/'bundle/data/session.json');cost=(time.time()-session['start_epoch'])*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 lines+=['## 覆盖与成本','',f"缺失{len(v['coverage']['missing_ids'])}、无效{len(v['coverage']['invalid_ids'])}；首答保留，不补旧答案、不按结果重发。",'',
 '训练只用原32名训练患者；评价固定原20名患者，均有历史暴露，不称全新holdout。36条理由逐字复用已有AI审读版本，不生成新reason、不改医生GT，不把评价数据用于训练。',
 '',f'截至{stamp}，09:36:01起新增窗口GPU估算¥{cost:.3f}/20，API原80元累计0；含准备、等待、加载、编译和回传。不自动关机或释放。',
 '', ('完整状态已回传。' if returned else '最终48步完整状态已在远端保存；本地已收到160条评价和训练完成记录，大文件仍在回传。')+'loss/梯度检查不等于分类价值，标签成绩也不证明同次reason自洽已解决。',
 '',f'[完整统计]({a.arm}_{a.scope}.json) · [固定方案](../../tasks/138_rationale_tasks/PROTOCOL.md)']
 text='\n'.join(lines).rstrip()+'\n';(O/(a.arm+'_'+a.scope+'.md')).write_text(text,encoding='utf-8');(O/'report.md').write_text(text,encoding='utf-8')
 print(json.dumps(dict(arm=a.arm,scope=a.scope,delta_MCC=s['delta_MCC'],delta_correct=s['delta_correct'],delta_false_S=s['delta_false_S'])))
if __name__=='__main__':main()
