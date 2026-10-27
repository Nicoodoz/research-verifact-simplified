"""Render full numerical disclosure from already frozen, complete101 analyses."""
from pathlib import Path
import json
import common101 as c

def table(tt):
 lines=['|配置|MCC|PA|正确数|错误支持/non-S|Macro-F1|NS召回|NA召回|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for arm,z in tt.items():lines.append(f"|{arm}|{z['mcc']:.4f}|{z['percent_agreement']:.2%}|{z['correct']}/{z['n']}|{z['false_S']}/{z['non_S']}|{z['Macro_F1']:.4f}|{z['per_class']['Not Supported']['recall']:.2%}|{z['per_class']['Not Addressed']['recall']:.2%}|")
 return '\n'.join(lines)
def pairs(pp):
 ll=['|候选−参照|救回/误伤/净正确|ΔMCC [95%患者区间]|ΔPA百分点|NS救回/误伤|NA救回/误伤|','|---|---:|---|---:|---:|---:|']
 for key,z in pp.items():
  ci=z['paired']['metrics']['mcc']['ci95'];r=z['rescue_by_GT'];h=z['harm_by_GT']
  ll.append(f"|{z['candidate']}−{z['base']}|{z['rescue']}/{z['harm']}/{z['net']:+d}|{z['delta_MCC']:+.4f} [{ci[0]:+.4f},{ci[1]:+.4f}]|{z['delta_PA']*100:+.2f}|{r.get('Not Supported',0)}/{h.get('Not Supported',0)}|{r.get('Not Addressed',0)}/{h.get('Not Addressed',0)}|")
 return '\n'.join(ll)
def write(path,text):Path(path).write_bytes((text.rstrip()+'\n').encode('utf-8'))
def main():
 a=c.read(c.OUT/'analysis.json');cost=c.read(c.OUT/'cost_ledger.json');freeze=c.read(c.OUT/'execution_freeze.json');trigger=c.read(c.OUT/'trigger_freeze.json');decision=a['decision']
 blocks=['# 101 NS/NA定向复核（nsna_review）',f"\n完成预定600自然＋100压力、282触发病例双臂、24条双臂独立重复。nsna_plain：**{decision['nsna_plain']['status']}**；nsna_review：**{decision['nsna_review']['status']}**。原文对应检查实际额外增量门槛：**{decision['review_increment']['practical_extra']}**。默认不变，未使用PriorG。",'\n## 方法、强对照与研究边界',
 'verifact_ref为原作者发布reference原样＋DeepSeek V4 Flash 0731原作者式简洁Judge；不完整复现作者辅助格式整理链。nsna_plain为普通独立二分类复核；nsna_review先识别断言、定位原文、解释对应，再二分类。paper_r1是作者历史R1同ID预测，不是同期同模型对照。所有新调用使用同一当前千问AI端点、thinking-high、temperature0、max_tokens8192、n1、非流式，不新增示例、检索或摘要。',
 '首次Supported逐条保留；仅首次NS/NA触发，两复核读取完全相同的原claim/reference且不见首答标签/reason、GT或其他回答；逻辑调用数相同，提示及输出任务不同。复核只能选NS/NA，因此无法救回原false-S，也无法救回首次误拒的真实S；false-S严格不变是结构保证，不能作为新增安全收益。NS不是必须发现明确矛盾；涉及但不完整支持包括部分支持，泛相关主题也不自动算涉及。',
 '[冻结协议](../../tasks/101_nsna_review/protocol.md) · [唯一提示词/引用验证](../../tasks/101_nsna_review/prompts101.py) · [历史区别](../../tasks/101_nsna_review/history_difference.md)。两阶段分类及固定S集合不是算法原创；本轮检验任务适配及原文对应检查的实际增量。',
 '\n## 样本、缓存及执行事实',
 '开发仅100的32名确认患者：224条离线材料，按首答NS/NA各6条固定hash取12条做两臂接口检查，不按正确率选择或调prompt。确认使用098的40患者，原400自然及NS/NA各50压力原样保留；另从同40患者按GT×作者比例和固定hash补200不同自然命题，排除原500 ID。全部患者历史已有研究暴露，只称本轮患者隔离。',
 '旧098/100自然共同主表的NS/NA互混为37条/28患者；按两者各自基线全部有效记录为38条/28患者，差异来自共同有效分母，未据这批错误挑确认病例。全700确认ID、prompt和判据先冻结；随后完成必要首答，并只按首答生成触发及24重复清单。',
 '缓存审查保留完整请求/回执SHA与实际输入：初版误把097回执缺失的endpoint字段默认成当前端点，已在确认复核前统一排除全部15份，保留原盘点/冻结并另存更正。重新查到替代回执后只额外补5条原定命题，无重复成功请求。最终复用503份可核验098/100首答，新调用197份基线；098原500标签逐条保持。见[来源更正](cache_engineering_amendment.json)。',
 f"基线无效{len(a['baseline_invalid'])}条不触发、不补标签；自然基线有效{a['coverage']['natural']['valid_N']}/600，压力{a['coverage']['pressure']['valid_N']}/100。实际触发自然{a['coverage']['natural']['triggered']}、压力{a['coverage']['pressure']['triggered']}；两臂各282次首次复核＋24次重复。开发两臂各12次，全部新逻辑调用833次。",
 '格式异常按事前严格JSON/字段/stop/引文定位规则保留首答NS/NA，作为明确fallback进入系统表；不默认NA，不重发HTTP200。review引文只允许连续原文或唯一空白规范化定位，来源可定位不认证事件对应或医生真值。',
 '\n## 自然确认主结果（系统口径）',table(a['tables']['natural']),pairs(a['paired']['natural']),
 '主实用目标为ΔMCC≥0.02、净正确≥8、false-S和逐条S集合不变、真实NS/NA净正确增加。进一步检查压力任一类召回不损失超过10个百分点、新200方向、重复及患者区间；不根据实际结果调整门槛。',
 '\n## 新增200条与原400条', '\n### 新增200',table(a['tables']['additional200']),pairs(a['paired']['additional200']), '\n### 原400',table(a['tables']['original400']),pairs(a['paired']['original400']),
 '\n## 少数类压力（与自然分报）',table(a['tables']['pressure']),pairs(a['paired']['pressure']),
 '压力仅NS/NA各50，S召回不适用；固定三类Macro-F1仍包含零支持S类，不与自然总体PA合并。',
 '\n## 同调用数的增量、类别偏置与重复',
 f"原文对应检查额外门槛为自然review−plain净正确≥3、ΔMCC≥0.01及压力类别保护；本次实际额外门槛={decision['review_increment']['practical_extra']}，增量MCC区间支持={decision['review_increment']['MCC_CI_positive']}。review是否超过全NS/全NA偏置诊断MCC={decision['review_increment']['beats_class_bias']}。偏置诊断只改变相同触发集合，不是另外训练或择优部署的模型。",
 f"重复固定24条，组成{a['repetition']['panels']}；plain/review翻转{a['repetition']['flips']}。重复仍执行同一严格parser和fallback，第二答不替换首答。",
 '\n首次重复子集：',pairs(a['repetition']['first']), '\n第二次：',pairs(a['repetition']['second']),
 '\n## 无效、回退和分层',
 '\n|面板|有效N|触发|plain回退|review回退|两臂复核原生共同有效N|\n|---|---:|---:|---:|---:|---:|',
 *[f"|{name}|{z['valid_N']}|{z['triggered']}|{z['fallbacks']['nsna_plain']}|{z['fallbacks']['nsna_review']}|{a['strict_native_sensitivity'][name]['common_native_N']}|" for name,z in a['coverage'].items()],
 '\n完整三类precision/recall/F1、混淆矩阵、AC1、预测S假发现率和human/LLM表见[detailed_tables.md](detailed_tables.md)；[analysis.json](analysis.json)保存所有配对、患者净胜负、逐例救回/误伤及原生共同有效敏感性。有效性筛选仅作敏感性，不能替代包含fallback的部署主表。',
 '\n## API费用与平均推理开销',
 f"全任务实际{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200、{cost['retries']}次重试；新增目录价及未知预留**¥{cost['used_or_reserved_cny']:.6f}/30**，未知/未核实¥{cost['unknown_or_unverified_cny']:.6f}。含开发、基线补齐、所有复核和重复；没有结转130元旧预算，也未因有剩余预算增加实验。是usage估算而非实扣账单。[官方价格核实](../../tasks/101_nsna_review/pricing_verification.md) · [费用总账](cost_ledger.json)。",
 '\n|面板/方案|每命题平均调用数|平均串行调用时间秒|忙时无缓存元/命题|\n|---|---:|---:|---:|',
 *[f"|{panel}/{arm}|{z['average_calls']:.3f}|{z['mean_pipeline_seconds']:.2f}|{z['mean_peak_no_cache_cny']:.6f}|" for panel,tt in cost['deployment'].items() for arm,z in tt.items()],
 '部署估算把已付基线也计一次、每个触发复核计一次；研究缓存复用不意味着上线基线免费。表中不把24重复作为日常部署步骤，重复的实际收费已计入本次总账。使用相同病例的实际token按忙时无缓存价归一，避免缓存命中或峰谷差异制造成本优势。',
 '\n## 解释、决定与复核',
 '判据逐项见[decision.json](decision.json)。区间跨0不证明等效；患者bootstrap只条件于固定输出，不涵盖历史开发选择、服务变化或新医院泛化。两个复核的不同输出任务及引用失败都属于当前实现成本，不能仅凭解释文字宣称模型内部更懂证据。原GT依据完整EHR，发布reference仅是模型实际输入。',
 '执行者自检见[selfcheck.json](selfcheck.json)，不称独立审计。原始临床文本、全文解释及原生回执保持私有；公开仅ID、标签、引用位置/SHA和抽象类型。完成后停止本版实验，不自动增加规则、上下文、重训PriorG或继续prompt搜索。默认系统不变。']
 write(c.OUT/'report.md','\n\n'.join(blocks))
 details=['# 101完整分类与分层表','所有表采用固定S/NS/NA顺序，原GT不变。自然/压力、原400/新增200分别报告。']
 for name,tt in a['tables'].items():
  details += ['\n## '+name,table(tt)]
  for arm,z in tt.items():
   details += ['\n### '+arm,f"AC1={z['gwet_ac1']:.6f}；预测S假发现率={z['predicted_S_fdr']}。",'|类别|precision|recall|F1|\n|---|---:|---:|---:|']
   for label in c.LABELS:
    q=z['per_class'][label];details.append(f"|{label}|{(q['precision'] or 0):.4f}|{(q['recall'] or 0):.4f}|{(q['f1'] or 0):.4f}|")
   details.append('混淆矩阵（GT行/预测列S、NS、NA）：`'+json.dumps(z['confusion_matrix'])+'`。')
 details += ['\n## 复核原生共同有效敏感性']
 for name,z in a['strict_native_sensitivity'].items():details+=['\n### '+name,table(z['tables'])]
 write(c.OUT/'detailed_tables.md','\n\n'.join(details))
 print('report and detailed tables written')
if __name__=='__main__':main()
