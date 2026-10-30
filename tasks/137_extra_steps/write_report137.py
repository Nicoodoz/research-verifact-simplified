"""Render137 only from completed training and actual evaluation outputs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
R=Path(__file__).resolve().parents[2];O=R/'outputs/137_extra_steps';LABELS=['Supported','Not Supported','Not Addressed']
def table(scores):
 rows=['|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for name,m in scores.items():
  if name=='candidate':name='extra_steps137'
  recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  rows.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recall}|")
 return rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=['screen160','old500','full1817']);p.add_argument('--decision',required=True);a=p.parse_args()
 private=R/'.local_models/137_extra_steps/evidence/extra_steps';trained=json.loads((private/'training_done.json').read_text(encoding='utf-8'))
 assert (trained['steps'],trained['consumed'])==(518,4137)
 pointer=json.loads((private/'train/resume.json').read_text(encoding='utf-8'));assert pointer['step']==518
 checkpoint=private/'train'/pointer['slot'];metadata=json.loads((checkpoint/'checkpoint_complete.json').read_text(encoding='utf-8'))
 assert metadata['step']==518 and metadata['files']['adapter_model.safetensors']==trained['adapter_sha256']
 assert (checkpoint/'training_state.pt').stat().st_size>300_000_000 and (checkpoint/'adapter_model.safetensors').stat().st_size>150_000_000
 logs=[json.loads(s) for s in (private/'steps.jsonl').read_text(encoding='utf-8').splitlines()]
 logs=[r for r in logs if 369<r['step']<=518];assert {r['step'] for r in logs}==set(range(370,519))
 summary=dict(source_step=369,completed_step=518,additional_updates=149,additional_presentations=1192,total_presentations_since120=4137,
  source_pool=2945,training_patients=32,evaluation_patients=20,training_step_seconds=sum(r['seconds'] for r in logs),optimizer_update_receipts=len(logs),
  adapter_sha256=trained['adapter_sha256'],full_checkpoint_returned=True,classification_gain_not_inferred_from_loss=True)
 (O/'training_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 v=json.loads((O/(a.scope+'.json')).read_text(encoding='utf-8'));s=v['primary'];old=s['scores']['claim_repeat136'];new=s['scores']['candidate']
 prior='stage160_summary.md' if a.scope=='old500' else ('stage500_summary.md' if a.scope=='full1817' else None)
 if prior and (O/'report.md').exists() and not (O/prior).exists():(O/prior).write_bytes((O/'report.md').read_bytes())
 lines=['# 137 extra_steps：'+a.scope,'',a.decision,'',f"固定149个新增更新全部完成，全局369→518；新增1192次呈现。主比较共同有效{v['joint_valid_N']}/{v['expected_N']}。MCC {old['mcc']:.4f}→{new['mcc']:.4f}，正确{old['correct']}→{new['correct']}，false-S {old['false_S']}→{new['false_S']}/{new['non_S']}。",'',
  '## 同输入的权重更新比较','']+table(s['scores']|v['historical_on_primary_IDs'])
 lines+=['',f"## 三基线共同{v['three_baseline_common_N']}条",'']+table(v['three_baseline_common_scores'])
 lines+=['','primary的claim_repeat136与extra_steps137使用完全相同的136输入、384输出上限和parse105，仅权重更新；旧120原输入、107和132使用104提示，author_base9b/author_lora9b使用原作者提示及768上限。paper_r1是不同模型/系统的历史结果。不同覆盖不跨表直接作差。','',
  '## 面板与类别得失','','|面板|N|ΔMCC|Δ正确|Δfalse-S|','|---|---:|---:|---:|---:|']
 for name,x in v['panels'].items():lines.append(f"|{name}|{x['N']}|{x['delta_MCC']:+.4f}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
 lines+=['','|GT类别|救回|误伤|净正确|','|---|---:|---:|---:|']
 for label,x in s['changes']['by_class'].items():lines.append(f"|{label}|{x['rescued']}|{x['harmed']}|{x['rescued']-x['harmed']:+d}|")
 pd=s['patient_directions'];up=sum(x['correct_delta']>0 for x in pd);down=sum(x['correct_delta']<0 for x in pd)
 lines+=['',f"false-S新增{s['changes']['false_S_new']}、避免{s['changes']['false_S_avoided']}；患者正确数{up}升/{down}降/{len(pd)-up-down}持平。",'']
 for name,x in v['by_author'].items():lines.append(f"- {name}：正确{x['delta_correct']:+d}、false-S{x['delta_false_S']:+d}。")
 lines+=['','## 混淆矩阵','','行GT、列预测，S/NS/NA顺序。','']
 for name,m in s['scores'].items():
  lines += [('extra_steps137' if name=='candidate' else name),'','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
  for label,row in zip(['S','NS','NA'],m['confusion_matrix']):lines.append('|'+label+'|'+'|'.join(map(str,row))+'|')
  lines.append('')
 if 'patient_bootstrap' in s:
  ci=s['patient_bootstrap']['metrics']['mcc']['ci95'];lines += [f'1000次患者配对bootstrap的ΔMCC 95%区间[{ci[0]:+.4f}, {ci[1]:+.4f}]；不覆盖训练随机性、历史开发选择或新医院泛化。','']
 cost=(time.time()-1793374800)*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 lines+=['## 范围和成本','',f"无效{len(v['coverage']['invalid_ids'])}、缺失{len(v['coverage']['missing_ids'])}；不补旧答案、不重发成功或无效回答。全部原GT、claim、reference和实际尝试保留。",'',
  '训练32人、评价20人无交集，新增训练使用原顺序的1192条，未按评价错误选样本；所有患者有历史暴露，不称全新holdout。518步只包括120阶段与本次延续，不包含更早的107微调。',
  '',f'截至{stamp}，23:40窗口GPU累计估算¥{cost:.3f}/16，API0/80。加载、编译、等待、训练、推理和回传均计入；平台精确账单未核。完整模型/优化器/RNG已回传，不关机或释放。',
  '', 'loss下降、梯度正常不当作分类收益。本模型输出的标签来自同次原生生成；不得配上旧模型理由。当前不宣称reason自洽已解决，不自动升级默认。',
  '',f'[完整统计与三类precision/recall/F1]({a.scope}.json) · [训练完成摘要](training_summary.json) · [固定方案](../../tasks/137_extra_steps/PROTOCOL.md)','']
 (O/'report.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps(dict(scope=a.scope,N=v['joint_valid_N'],delta_MCC=s['delta_MCC'],delta_correct=s['delta_correct'],delta_false_S=s['delta_false_S'],GPU_CNY=cost)))
if __name__=='__main__':main()
