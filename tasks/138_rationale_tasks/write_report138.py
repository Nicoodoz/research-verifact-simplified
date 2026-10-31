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
 cp=P/a.arm/'evidence/train';pointer=read(cp/'resume.json');assert pointer['step']==48
 assert (cp/pointer['slot']/'training_state.pt').stat().st_size>300_000_000
 s=v['primary'];lines=['# 138 '+a.arm+'：'+a.scope,'',a.decision,'',f"已完成固定48步/384次呈现；目标{v['expected_N']}，实际有效{v['valid_N']}。本表与136使用相同输入，变化来自训练。",'',
 '## 同ID比较','']+table(s['scores']|v['historical_on_same_IDs'],a.arm)
 lines+=['',f"## 三个指定基线共同{v['three_baseline_common_N']}条",'']+table(v['three_baseline_common_scores'],a.arm)
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
  lines += [name+'混淆矩阵（行GT、列预测；S/NS/NA）','','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
  for g,row in zip(['S','NS','NA'],m['confusion_matrix']):lines.append('|'+g+'|'+'|'.join(map(str,row))+'|')
  lines.append('')
 if 'patient_bootstrap' in s:
  lo,hi=s['patient_bootstrap']['metrics']['mcc']['ci95'];lines += [f'1000次患者配对ΔMCC 95%区间[{lo:+.4f},{hi:+.4f}]；不涵盖训练随机性、历史选型或新医院泛化。','']
 if 'rationale_vs_replay' in v:
  x=v['rationale_vs_replay'];lines+=['## 与匹配标签回放的直接比较','']+table(x['scores'],'rationale_tasks')+[f"ΔMCC{x['delta_MCC']:+.4f}，Δ正确{x['delta_correct']:+d}，Δfalse-S{x['delta_false_S']:+d}。",'']
 else:lines+=['匹配标签回放对照尚无此范围的完整结果；此时不能把相对136的变化全部归因于理由任务。','']
 session=read(P/a.arm/'bundle/data/session.json');cost=(time.time()-session['start_epoch'])*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 lines+=['## 覆盖与成本','',f"缺失{len(v['coverage']['missing_ids'])}、无效{len(v['coverage']['invalid_ids'])}；首答保留，不补旧答案、不按结果重发。",'',
 '训练只用原32名训练患者；评价固定原20名患者，均有历史暴露，不称全新holdout。36条理由逐字复用已有AI审读版本，不生成新reason、不改医生GT，不把评价数据用于训练。',
 '',f'截至{stamp}，09:36:01起新增窗口GPU估算¥{cost:.3f}/20，API原80元累计0；含准备、等待、加载、编译和回传。不自动关机或释放。',
 '', '完整状态已回传。loss/梯度检查不等于分类价值，标签成绩也不证明同次reason自洽已解决。',
 '',f'[完整统计]({a.arm}_{a.scope}.json) · [固定方案](../../tasks/138_rationale_tasks/PROTOCOL.md)']
 text='\n'.join(lines).rstrip()+'\n';(O/(a.arm+'_'+a.scope+'.md')).write_text(text,encoding='utf-8');(O/'report.md').write_text(text,encoding='utf-8')
 print(json.dumps(dict(arm=a.arm,scope=a.scope,delta_MCC=s['delta_MCC'],delta_correct=s['delta_correct'],delta_false_S=s['delta_false_S'])))
if __name__=='__main__':main()
