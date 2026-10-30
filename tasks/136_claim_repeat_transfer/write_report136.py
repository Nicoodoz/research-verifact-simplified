"""Render actual136 statistics; preserve prior stage summaries."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
R=Path(__file__).resolve().parents[2];O=R/'outputs/136_claim_repeat_transfer';LABELS=['Supported','Not Supported','Not Addressed']
def table(scores):
 rows=['|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for name,m in scores.items():
  name='claim_repeat' if name=='candidate' else name
  recalls='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  rows.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recalls}|")
 return rows
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=['screen160','old500','full1817']);parser.add_argument('--decision',required=True);a=parser.parse_args()
 v=json.loads((O/(a.scope+'.json')).read_text(encoding='utf-8'));p=v['primary'];new=p['scores']['candidate'];old=p['scores']['full_pool120']
 prior='stage160_summary.md' if a.scope=='old500' else ('stage500_summary.md' if a.scope=='full1817' else None)
 if prior and (O/'report.md').exists() and not (O/prior).exists():(O/prior).write_bytes((O/'report.md').read_bytes())
 lines=['# 136 claim_repeat迁移：'+a.scope,'',a.decision,'',f"实际目标{v['expected_N']}，主比较共同有效{v['joint_valid_N']}。MCC {old['mcc']:.4f}→{new['mcc']:.4f}，正确{old['correct']}→{new['correct']}，false-S {old['false_S']}→{new['false_S']}（非S={new['non_S']}）。无效不填旧答案。",'',
  '## 同120权重与104接口的主比较','']
 lines+=table(p['scores']|v['historical_on_primary_IDs'])
 lines+=['',f"## 与三个基线的共同{v['three_baseline_common_N']}条",'']+table(v['three_baseline_common_scores'])
 lines+=['','主表与三个基线表的有效交集可能不同，不跨表相减。author_base9b/author_lora9b使用原作者提示与768上限；本候选、107、120、132使用104任务接口及384上限。paper_r1是不同模型和系统的作者历史参照；详见[统一基线](../134_author_baselines/report.md)。','',
  '## 原面板与类别得失','','|面板|共同N|MCC|PA|正确|FS/非S|Δ正确|ΔFS|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for name,x in v['panels'].items():
  m=x['scores']['candidate'];lines.append(f"|{name}|{x['N']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
 lines+=['','|GT类别|救回|误伤|净正确|','|---|---:|---:|---:|']
 for name,x in p['changes']['by_class'].items():lines.append(f"|{name}|{x['rescued']}|{x['harmed']}|{x['rescued']-x['harmed']:+d}|")
 pts=p['patient_directions'];up=sum(x['correct_delta']>0 for x in pts);down=sum(x['correct_delta']<0 for x in pts)
 lines+=['',f"false-S避免{p['changes']['false_S_avoided']}次、新增{p['changes']['false_S_new']}次。患者正确数{up}升/{down}降/{len(pts)-up-down}持平。",'']
 for name,x in v['by_author'].items():lines.append(f"- {name}：正确{x['delta_correct']:+d}、false-S{x['delta_false_S']:+d}。")
 lines+=['','## 混淆矩阵','','行GT、列预测，固定S/NS/NA顺序。','']
 for name,m in p['scores'].items():
  name='claim_repeat' if name=='candidate' else name
  lines += [name,'','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
  for label,row in zip(['S','NS','NA'],m['confusion_matrix']):lines.append('|'+label+'|'+'|'.join(map(str,row))+'|')
  lines.append('')
 if 'patient_bootstrap' in p:lines+=['患者配对区间与风险区间已保留在统计JSON。区间不覆盖历史选型、重训或新医院泛化。','']
 lines+=['## 输入、覆盖与成本','',f"缺失{len(v['coverage']['missing_ids'])}，无效{len(v['coverage']['invalid_ids'])}；每个ID只保留首次返回，不因标签好坏重发。",'']
 if 'input_cost' in v:
  c=v['input_cost'];lines.append(f"重复原claim使每条输入平均增加{c['mean_extra_tokens']:.1f} tokens，中位数{c['median_extra_tokens']:.1f}、最大{c['max_extra_tokens']}；总输入增加{c['relative_total_input_increase']:.2%}。完整reference不变，输出上限仍384。")
 cost=(time.time()-1793374800)*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 lines+=['',f'截至{stamp}，23:40窗口GPU累计估算¥{cost:.3f}/16，包含交接、准备、等待、加载、编译、推理与回传；新增API0/80。没有新训练，未关机或释放，平台精确账单未核。',
  '', '全部20名患者有历史研究暴露，属于开发/选型证据。原医生GT、claim、reference和全部尝试保留，不使用评价数据训练。本方法只改变原生输入，不后接分类器或修改模型标签；未证明理由完整、正确或与标签逐例自洽，不能把旧reason配给本次标签。',
  '',f"[统计、三类precision/recall/F1与患者明细]({a.scope}.json) · [逐ID有效状态]({a.scope}_receipt_status_sanitized.jsonl) · [固定方案](../../tasks/136_claim_repeat_transfer/PROTOCOL.md)",'']
 (O/'report.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps(dict(scope=a.scope,N=v['joint_valid_N'],delta_MCC=p['delta_MCC'],delta_correct=p['delta_correct'],delta_false_S=p['delta_false_S'],cost_CNY=cost)))
if __name__=='__main__':main()
