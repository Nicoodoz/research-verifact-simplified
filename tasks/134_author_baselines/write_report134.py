"""Summarize completed1817 only; preserves preceding stage reports."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,time
R=Path(__file__).resolve().parents[2];P=R/'.local_models/134_author_baselines';O=R/'outputs/134_author_baselines'
LABELS=('Supported','Not Supported','Not Addressed')

def main():
 d=json.loads((O/'full1817.json').read_text(encoding='utf-8'))
 assert d['scope']=='full1817' and d['expected_N']==1817
 assert all(c['received']==1817 and not c['missing_ids'] for c in d['coverage'].values())
 if not (O/'stage500_summary.md').exists():(O/'stage500_summary.md').write_bytes((O/'report.md').read_bytes())
 scores=d['panels']['all']['scores'];N=d['common_valid_N']
 lines=['# 134：完整1817条统一基线比较','',
  f'两个9B均已完成1817个目标ID的首次回执，paper_r1完整历史覆盖直接复用。严格共同有效{N}条；各自覆盖、缺失和无效另列，未补旧答案。',
  '','## 核心比较：严格共同有效ID','','|配置|MCC|PA|正确|false-S/真实非S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for arm,m in scores.items():
  recall='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.2%}" for g in LABELS)
  lines.append(f"|{arm}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{m['macro_F1']:.4f}|{recall}|")
 lines+=['','## 适配器收益、风险和类别得失','']
 for key,v in d['panels']['all']['comparisons'].items():
  if not key.startswith('author_lora9b_vs_'):continue
  ref=v['reference_model'];c=v['changes']
  change='；'.join(f"{g}救回{c['by_class'][g]['rescued']}／误伤{c['by_class'][g]['harmed']}" for g in LABELS)
  directions=v['patient_directions'];up=sum(x['correct_delta']>0 for x in directions);down=sum(x['correct_delta']<0 for x in directions)
  text=f"相对{ref}：MCC {v['delta_MCC']:+.4f}、正确{v['delta_correct']:+d}、false-S {v['delta_false_S']:+d}。{change}。患者正确数{up}升、{down}降、{len(directions)-up-down}持平。"
  b=v.get('patient_bootstrap')
  if b:
   lo,hi=b['metrics']['mcc']['ci95'];text+=f' 1000次患者配对bootstrap的ΔMCC 95%区间[{lo:+.4f}, {hi:+.4f}]。'
  lines.extend([text,''])
 lines+=['三类净得失不能替代逐类召回；MCC单点下降也不独自决定去留。区间仅描述已有开发队列，不覆盖历史选型、重训或新医院泛化。',
  '','## 原面板与新增覆盖','','|面板|共同有效N|适配器MCC|PA|正确|false-S/非S|相对未微调 Δ正确/Δfalse-S|相对104接口120 Δ正确/Δfalse-S|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for group in ['natural400','pressure100','new1317','history103_180']:
  if group not in d['panels']:continue
  panel=d['panels'][group];m=panel['scores']['author_lora9b'];a=panel['comparisons']['author_lora9b_vs_author_base9b'];b=panel['comparisons']['author_lora9b_vs_full_pool120']
  lines.append(f"|{group}|{panel['N']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{a['delta_correct']:+d}/{a['delta_false_S']:+d}|{b['delta_correct']:+d}/{b['delta_false_S']:+d}|")
 lines+=['','自然400、压力100和新增1317按冻结成员报告；压力面板不含真实S，不能把其S召回填成0。上表N是实际共同有效数，完整原面板及各自覆盖见详细表。',
  '','## 患者与作者来源','']
 for author,v in d['by_author'].items():
  a=v['author_lora_vs_base'];b=v['author_lora_vs120']
  lines.append(f"- {author}，N={v['N']}：相对未微调正确{a['delta_correct']:+d}／false-S {a['delta_false_S']:+d}；相对104接口120正确{b['delta_correct']:+d}／false-S {b['delta_false_S']:+d}。")
 lines+=['','## 输出与完整覆盖','','|模型|返回/目标|有效|无效|有效标签中缺reason|','|---|---:|---:|---:|---:|']
 for arm,c in d['coverage'].items():lines.append(f"|{arm}|{c['received']}/1817|{c['valid']}|{len(c['invalid_ids'])}|{len(c['missing_reason_valid_ids'])}|")
 lines+=['','各自有效集合的原始成绩（不同分母不直接作差）：','',
  '|模型|有效N|MCC|PA|正确|false-S/非S|','|---|---:|---:|---:|---:|---:|']
 for arm,m in d['standalone_scores'].items():lines.append(f"|{arm}|{m['n']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|")
 lines+=['','缺reason、JSON异常和明确语义矛盾分别看待。一个流畅reason可能只支持比原命题更弱的说法；当前标签成绩不是解释可靠性或临床推理机制证明。原始标签与同次生成reason均保留，没有后接分类器、投票或标签修正规则。',
  '','## 公平范围与复用','',
  '- author_base9b与author_lora9b只差120 final369适配器；两者使用相同原作者提示、完整作者reference、BF16、关闭thinking、greedy、768输出上限和解析规则。每臂20条旧回执经过配置与ID核对后复用，其余1797条为新回执。',
  '- 120继承107监督后在原32名梯度患者2945条上继续369步；107为原196条标签微调。当前复用已有权重不代表原训练没有成本。没有评价患者进入本轮梯度训练。',
  '- 107、120原接口和132使用104修改提示及384输出上限，与原作者接口存在提示、输出合同和预算差异。不能把两者差异单独归因于提示词。',
  '- paper_r1是原作者R1-70B历史系统；同ID对比保留模型及系统差异。没有重跑70B或新增收费API。',
  '- 103旧180条的thinking4096＋final768结果单列历史子集，不混入关闭thinking基线。105同104提示的未微调9B缓存仅在真实有效交集展示，旧15条无效不补。',
  '- 全部患者已有历史研究暴露。本队列是开发／选型证据，不称独立外部测试，不自动升级默认。',
  '','## 资源与后续','']
 session=json.loads((P/'session.json').read_text());stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
 cost=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600
 lines += [f'截至{stamp}，本轮从2026-10-30 23:40起累计GPU墙钟估算¥{cost:.3f}/16，包含交接、准备、等待、加载、编译和回传。新增收费API ¥0/80。平台精确账单未核；未自动关机或释放，留机继续计费。',
  '', '本报告完成统一基线部分；是否执行下一项原生输入优化或模型适配，依据上述真实结果及剩余预算决定。任务完成不等于本轮持续目标结束。',
  '', '[完整表、混淆矩阵和历史接口子集](full1817.md) · [机器可读结果与区间](full1817.json) · [覆盖清单](full1817_coverage.json) · [500阶段原总结](stage500_summary.md) · [实时进度](progress.md)','']
 (O/'report.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps({'report_written':True,'common_valid':N,'GPU_CNY_at_report':cost}))

if __name__=='__main__':main()
