"""Render actual133 results; no result is inferred from optimizer diagnostics."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
from records133 import R,Q,ARMS,read
O=R/'outputs/133_shuffle_repeat';LABELS=['Supported','Not Supported','Not Addressed']
def table(scores):
 result=['|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for name,m in scores.items():
  recalls='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  result.append(f"|{name}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recalls}|")
 return result
def details(p):
 out=[f"ΔMCC {p['delta_MCC']:+.4f}，Δ正确{p['delta_correct']:+d}，Δfalse-S{p['delta_false_S']:+d}。",'','|GT|救回|误伤|净正确|','|---|---:|---:|---:|']
 for g,x in p['changes']['by_class'].items():out.append(f"|{g}|{x['rescued']}|{x['harmed']}|{x['rescued']-x['harmed']:+d}|")
 pts=p['patient_directions'];up=sum(x['correct_delta']>0 for x in pts);down=sum(x['correct_delta']<0 for x in pts)
 out+=['',f"false-S新增{p['changes']['false_S_new']}、避免{p['changes']['false_S_avoided']}；患者正确数{up}升/{down}降/{len(pts)-up-down}平。",'']
 if 'patient_bootstrap' in p:
  ci=p['patient_bootstrap']['metrics']['mcc']['ci95'];out += [f'1000次患者配对ΔMCC 95%区间[{ci[0]:+.4f}, {ci[1]:+.4f}]。','']
  out+=['|指标|变化（百分点）|95%患者区间|','|---|---:|---|']
  for name,x in p['risk_and_recall_bootstrap'].items():
   lo,hi=x['ci95'];out.append(f"|{name}|{100*x['delta']:+.2f}|[{100*lo:+.2f}, {100*hi:+.2f}]|")
  out.append('')
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['screen160','old500','full1817'],required=True);ap.add_argument('--decision',required=True);args=ap.parse_args()
 v=read(O/(args.scope+'.json'));done=read(Q/'evidence/shuffle_repeat/training_done.json');assert (done['steps'],done['consumed'])==(369,2945)
 pointer=read(Q/'evidence/shuffle_repeat/train/resume.json');checkpoint=Q/'evidence/shuffle_repeat/train'/pointer['slot'];assert pointer['step']==369
 assert (checkpoint/'training_state.pt').stat().st_size>300_000_000 and (checkpoint/'adapter_model.safetensors').stat().st_size>150_000_000
 logs=[json.loads(x) for x in (Q/'evidence/shuffle_repeat/steps.jsonl').read_text().splitlines()]
 assert {x['step'] for x in logs}==set(range(1,370))
 prior='stage160_summary.md' if args.scope!='screen160' else None
 if prior and (O/'report.md').exists() and not (O/prior).exists():(O/prior).write_bytes((O/'report.md').read_bytes())
 lines=['# 133 shuffle_repeat：'+args.scope,'',args.decision,'',
  '固定118027种子和新顺序，原107权重起点、2945条原训练数据、369步均完成；没有按评价挑选checkpoint或种子。与120的差异包含数据顺序及随机训练实现，不能只归因于顺序。','']
 for arm,p in v['seed_comparison'].items():
  lines+=['## 相同输入下的训练实现差异：'+arm,'']+table(p['scores'])+['']+details(p)
 p=v.get('within_new_seed')
 if p:
  lines+=['## 同一新模型上的输入效应','']+table(p['scores'])+['']+details(p)
  lines+=['|面板|N|ΔMCC|Δ正确|Δfalse-S|','|---|---:|---:|---:|---:|']
  for name,x in v['panels'].items():lines.append(f"|{name}|{x['N']}|{x['delta_MCC']:+.4f}|{x['delta_correct']:+d}|{x['delta_false_S']:+d}|")
  lines.append('')
  for name,x in v['by_author'].items():lines.append(f"- {name}来源：Δ正确{x['delta_correct']:+d}、Δfalse-S{x['delta_false_S']:+d}。")
  lines+=['','### 新模型混淆矩阵','','行GT、列预测，S/NS/NA顺序。','']
  for name,m in p['scores'].items():
   if name=='paper_r1':continue
   lines += [name,'','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
   for label,row in zip(['S','NS','NA'],m['confusion_matrix']):lines.append('|'+label+'|'+'|'.join(map(str,row))+'|')
   lines.append('')
 else:lines+=['## 输入配对尚未齐全','','当前只能报告已完成输入，不能把尚未运行的claim_repeat填成0或推断其效应。','']
 lines += [f"## 指定基线共同有效{v['three_baseline_common_N']}条",'']+table(v['common_scores'])+['',
  'author_base9b/author_lora9b是原作者提示＋768输出上限；107、120及本复验使用104接口＋384输出上限。claim_repeat只在完整reference之后重述原claim，权重相同。paper_r1为作者不同模型/系统的历史结果。不同有效交集不跨表相减。','',
  '## 覆盖、费用与边界','']
 for arm,c in v['coverage'].items():lines.append(f"- {arm}：收到{c['received_N']}/{c['target_N']}，有效{c['valid_N']}，无效{len(c['invalid_ids'])}，缺失{len(c['missing_ids'])}。")
 session=read(Q/'session.json');cost=(time.time()-session['start_epoch'])*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 lines+=['',f'截至{stamp}，09:36:01起新增GPU估算¥{cost:.3f}/20；API原80元累计仍为0。含准备、加载、编译、等待、回传及分析，不自动关机或释放。',
  '', '原32训练患者与20评价患者无交集；所有患者有历史暴露，不称新holdout。原GT、claim、reference和全部尝试保留。无效不补旧答案，不按标签重发。',
  '', '单次固定复验只能补充稳定性证据，不能估计所有训练随机性；患者bootstrap也不涵盖历史开发选择或新医院泛化。梯度正常、loss下降、格式完整均不替代分类收益。reason自洽尚未由本实验验证，不将旧reason配给新标签。',
  '',f'[完整统计]({args.scope}.json) · [执行协议](../../tasks/133_shuffle_repeat/EXECUTION_20261031.md) · [当前状态](../../tasks/133_shuffle_repeat/CURRENT.md)','']
 (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
 print(json.dumps(dict(scope=args.scope,GPU_CNY=cost,paired_input_effect_available=p is not None)))
if __name__=='__main__':main()
