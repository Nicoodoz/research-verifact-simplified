"""Chinese decision report, one-page night handoff and combined fee rollup."""
from collections import Counter
from decimal import Decimal
import json,statistics,sqlite3
import common100 as c
import runtime100 as rt

def table(pp):
 out=['|配置|MCC|PA|正确/N|false-S/non-S|NS/NA召回|','|---|---:|---:|---:|---:|---|']
 for a,t in pp['tables'].items():out.append(f"|{a}|{t['mcc']:.4f}|{t['percent_agreement']:.2%}|{t['correct']}/{t['n']}|{t['false_S']}/{t['true_non_S']}|{t['per_class']['Not Supported']['recall'] or 0:.1%}/{t['per_class']['Not Addressed']['recall'] or 0:.1%}|")
 return '\n'.join(out)
def comparetable(pairs):
 out=['|候选−参考|救回/伤害|ΔMCC [95%患者区间]|ΔPA|Δfalse-S率 [95%区间]|','|---|---:|---|---:|---|']
 for name,p in pairs.items():
  m=p['paired']['metrics']['mcc'];a=p['paired']['metrics']['percent_agreement'];ci=p['false_S_rate_delta_CI95'];f='不适用' if ci is None else f"{p['false_S_rate_delta']:+.2%} [{ci[0]:+.2%},{ci[1]:+.2%}]"
  out.append(f"|{p['candidate']}−{p['base']}|{p['rescue']}/{p['harm']}|{m['delta']:+.4f} [{m['ci95'][0]:+.4f},{m['ci95'][1]:+.4f}]|{a['delta']:+.2%}|{f}|")
 return '\n'.join(out)
def main():
 assert not (c.PRIVATE/'run.lock').exists()
 branch=c.read(c.OUT/'branch_decision.json');b=c.read(c.OUT/'handoff_budget_snapshot.json');f=c.read(c.OUT/'execution_freeze.json');old=c.read(c.ROOT/'outputs/098_p90_native_confirmation/analysis.json');oldcost=c.read(c.ROOT/'outputs/098_p90_native_confirmation/cost_ledger.json');d98=old['decision']
 mode='cross_model_confirmation' if branch['branch']=='cross_model' else 'confirmation' if (c.OUT/'confirmation_analysis.json').exists() else 'development'
 a=c.read(c.OUT/(mode+'_analysis.json'));decision=a['decision'];status=decision.get('status','失败停止');winner=decision.get('winner');summary=rt.summary()
 con=rt.db();attempts=con.execute('SELECT charge,status,folder FROM attempts').fetchall();con.close();unknown=0.
 for amount,http,folder in attempts:
  p=c.ROOT/folder;account=c.read(p/'accounting.json')
  if account['basis'].startswith('reserved'):unknown+=amount
 rollup=dict(**summary,utc=c.utc(),old098_prior_to_instruction_cny=b['previous098_cost_and_unknown_cny'],whole098_cost_or_reserved_cny=oldcost['used_or_reserved_cny'],old098_unknown_preserved_cny=oldcost['unknown_or_unverified_reservation_cny'],new100_unknown_or_unverified_cny=unknown,
  prior099_not_counted=True,task098_cumulative_cap_cny=50,abnormal_margin_cny=5,price_basis='Verified current catalog including official cache rate, never promo or account credit; no-cache worst-output planning',independent_financial_bill=False)
 assert rollup['whole098_cost_or_reserved_cny']<=50 and rollup['total_new_cost_or_reserved_cny']<=130
 c.put(c.OUT/'cost_ledger.json',rollup)
 dev=c.read(c.OUT/'development_analysis.json') if (c.OUT/'development_analysis.json').exists() else None
 text=[f'# 100：今晚预注册后续研究\n\n**最终类别：{status}。** 实际分支：{branch["branch"]}；候选：{winner or "全部未获准晋级"}。默认系统未改变；独立审计未执行。',
  '## 098先行结论\n\n098已完整完成2120目标请求，Q构造2次另计；主面板、压力、F80、四臂重复60均完成。' + f"P对O/Q/C原门槛通过为{d98['gates']['O']['pass_all']}/{d98['gates']['Q']['pass_all']}/{d98['gates']['C']['pass_all']}，压力检查={d98['pressure_checks']}，重复反向={d98['repeat_direction_reversal']}。按本次用户要求，只有recommend_replace_C=true才走跨模型；本轮为{d98['recommend_replace_C']}。[098正式报告](../098_p90_native_confirmation/report.md)。\n\n"+table(old['panels']['natural']),
  '## 样本、冻结和公平条件\n\n32名确认患者是100人排除098评价40与示例开发28后的余集；本轮开发实际'+str(f['stage_counts']['development']['patients'])+'人，'+('确认实际32人' if mode!='development' else '确认预冻32人；开发全部淘汰时不发生确认调用')+'，开发与确认患者互不重叠。全部患者历史已暴露，只称本轮患者隔离确认。开发48自然+NS/NA各12，确认预冻192自然+NS/NA各16，确认自然16条独立重复。原始GT只抽样/评价，不进构造。原定规模的最贵完整路径141.81元，事前按用户规定整体降档后121.30元；包含为098原50元上限余量完整预留、每次8192输出、无缓存/别名节约。实际便宜不扩样。[协议](../../tasks/100_preregistered_followup/protocol.md) · [输入冻结](execution_freeze.json) · [预算](budget_plan.json)。',
  '证据分支固定与098同DeepSeek0731、同简洁Judge、thinking-high、temperature0、max8192；无示例/后处理。O=发布reference，C=冻结C48。S24/L24遍历同一完整eligible语料，008词法、640字符块和BM25原函数，031实际6125段的索引字段/文本/ID已逐一核对。L以最高子块分数排完整note；S完整短块逐例配平L实际JSON渲染token预算；EHR-all给全部合规原note。仅同note相接/空白间隔可合并；原文完整覆盖恢复原TEXT。合法范围沿既有住院日历日期、排除discharge summary，不临改截止时间或HADM规则。原note的实际HADM保留供回查。',
  '原始未转义语料最长299672 tokenizer tokens；本轮冻结最大全请求输入预计310204，低于0731平台1M上下文，全部EHR-all均完整，无长患者剔除或截断。长度预算计Input JSON转义后reference内部，API实际prompt usage另列，公开tokenizer不冒充已证明内部模板逐token一致。C只作参考，不参与候选筛选。相同body跨臂只共享本轮首答，既定重复独立发送。[容量与别名](capacity_and_alias_preflight.json) · [来源/范围](source_inventory.json)。Original仅作者历史R1同ID预测，不能替代同期O；098的F是完整历史示例，100的EHR-all是本患者全部合规notes、无示例，二者不同。']
 if dev:
  text+=['## 开发排雷与唯一候选\n\n'+table(dev['panels']['natural'])+'\n\n额外NS/NA压力：\n\n'+table(dev['panels']['pressure']),
   '开发筛选逐项结果（未按显著与否或小阳性决定扩量）：\n\n'+'\n'.join(f"- {arm}：eligible={z['eligible']}，否决={','.join(z.get('veto',[])) or '无'}，路径A/B={z.get('path_A')}/{z.get('path_B')}。" for arm,z in dev['decision']['checks'].items())+f"\n\n唯一晋级：{dev['decision']['winner'] or '无；按预注册停止，不运行确认收费'}。完整共同有效口径/覆盖见development_analysis。"]
 if mode!='development':
  text+=['## 完整确认结果\n\n自然分布：\n\n'+table(a['panels']['natural'])+'\n\n额外NS/NA压力：\n\n'+table(a['panels']['pressure']),
   comparetable(a['panels']['natural']['paired']),
   '压力配对：\n\n'+comparetable(a['panels']['pressure']['paired']),
   f"固定同body重复：冻结{a['stability']['frozen_N']}条、共同有效{a['stability']['common_N']}条，标签翻转{a['stability']['flips']}；第二答不替换首答。首次/第二次三类指标、配对与核心方向完整保留在{mode}_analysis.json。",
   '实用门槛与区间的正式判定见[confirmation_decision.json](confirmation_decision.json)。本轮L−O ΔMCC=−0.0205、ΔPA=+0.53个百分点、false-S率+5.41个百分点，MCC与风险两路线点值均未通过，并非仅差显著性。相对C和S24同样未过实用门槛，完整note机制未成立。\n\n正确数变化来自Supported净+4、NS净−1、NA净−2；PA略升掩盖少数类损失。重复O/L标签未变且L−O MCC仍为负，没有可声称稳定的核心优势；机器stability_pass字段不能在主路线未通过时单独读成“稳定性通过”，详见[错误转移与字段解释](error_transfer_analysis.md)。原预测和判定未改写。只有实用点值和主要改善量患者95%区间均支持且压力/重复合格才叫确认通过；区间跨0不等于等效。']
 text+=['## 长度、实际操作、覆盖和费用\n\n下表为当前实际最后执行阶段的各臂首次调用，cache/别名实际均分费和独立部署无缓存费分开。\n\n|臂|例数|平均输入token|平均输出含思考|实际均分元/例|无缓存元/例|\n|---|---:|---:|---:|---:|---:|\n'+'\n'.join(f"|{arm}|{z['N']}|{z['mean_input']:.1f}|{z['mean_output']:.1f}|{z['mean_actual_allocated_cny']:.6f}|{z['mean_no_cache_cny']:.6f}|" for arm,z in a['costs'].items()),
  '实际同body/长度不是名义上的不同臂：开发72条中S=L43、L=E45；确认224条中S=L90、L=E92。S/L最大离散token缺口分别199/115；没有截断L以凑长度。确认实际API输入L−S平均3.53 tokens、P95为15、最大115，长度对照有效。自然192条首次API平均输入O/C/S/L为7452/2950/21053/21057 tokens；无缓存每例约0.01331/0.00646/0.03419/0.03404元，L约C的5.27倍而没有实用优势。[实际输入与操作](input_operation_summary.json)。\n\n完整覆盖[coverage.csv](coverage.csv)、三类P/R/F1/混淆/预测S假发现率与作者分层[detailed_tables.md](detailed_tables.md)单列；自然冻结192，O/C/S/L有效190/192/191/191，主共同189。压力32共同32，重复16共同15。无效不补旧答案或NA、不重发。',
  f"098此前已发生及未知¥{b['previous098_cost_and_unknown_cny']:.6f}不占新额度，原未知预留仍留原账；098原任务累计¥{oldcost['used_or_reserved_cny']:.6f}/50。本指令新增098 ¥{summary['new098_cost_or_reserved_cny']:.6f}＋100 ¥{summary['task100_cost_or_reserved_cny']:.6f}＝**¥{summary['total_new_cost_or_reserved_cny']:.6f}/130**；100未知¥{unknown:.6f}。逐次发送均先预留，未优惠目录价结算，重试/在途/未知不清零；099历史额度未叠加。[总账](cost_ledger.json)。不是账户实扣账单，无GPU租金。",
  '## 自检与解释边界\n\n使用统一evaluate/paired_compare和1000次患者配对bootstrap，独立混淆矩阵/sklearn/Decimal复核；不是独立调查者或医生审计。GT面对完整参考EHR，本轮all是冻结合法日历范围内全部notes，不能冒充患者终身记录。32名患者隔离只消除本轮开发患者重叠，不覆盖历史开发选择或新医院泛化。raw改判不是内部推理或新医生GT。[执行者自检](selfcheck.json)。\n\n确认失败或仅点值改善，不通过追加同面板/更改24K/换样本救成绩；完成本轮后不自动启动新实验。']
 c.put(c.OUT/'report_content.json',dict(status=status,mode=mode,winner=winner,report_sections=len(text)))
 report='\n\n'.join(text)+'\n';p=c.OUT/'report.md'
 if p.exists():assert p.read_text(encoding='utf-8')==report
 else:p.write_bytes(report.encode())
 n98=old['panels']['natural'];brief=f'''# 今晚结论：098与100

**最终选择：{status}。** 100实际分支为{branch['branch']}，晋级方案为{winner or '无，全部开发候选未获准晋级'}。

098已完整完成全部2120目标请求，另2次Q构造；P对O/Q/C分别通过={d98['gates']['O']['pass_all']}/{d98['gates']['Q']['pass_all']}/{d98['gates']['C']['pass_all']}。压力/重复及三类代价详见098报告，未把未跑完当阴性，也未只赢O就声称保护机制成立。

100采用事前预算降档：开发48自然+24压力（{f['stage_counts']['development']['patients']}人），确认预冻192自然+32压力（32人），固定重复16。开发/确认患者隔离，均有历史研究暴露；方法和规模未按新成绩调整。

实际最后执行阶段：{mode}。自然同ID表：

{table(a['panels']['natural'])}

自然与额外NS/NA分开；完整压力、救回/伤害、患者95%区间、重复与human/LLM在[正式报告](report.md)和阶段analysis。默认Judge/原GT/原始数据未改变，没有PriorG或GPU部署。

新增费用：098续跑¥{summary['new098_cost_or_reserved_cny']:.6f}，100 ¥{summary['task100_cost_or_reserved_cny']:.6f}，合计¥{summary['total_new_cost_or_reserved_cny']:.6f}/130；100未知预留¥{unknown:.6f}，旧098未知仍保留原账。未为花完预算追加方法或样本。

明天最值得做的一个动作：拿这张同模型确认表与导师收敛论文主线，明确P90和本版24K完整note路线停止；不再凭开发阳性追加投入。
'''
 bp=c.OUT/'night_summary.md'
 if bp.exists():assert bp.read_text(encoding='utf-8')==brief
 else:bp.write_bytes(brief.encode())
 print(c.canonical(dict(status=status,winner=winner,mode=mode,total_new_cny=summary['total_new_cost_or_reserved_cny'])))
if __name__=='__main__':main()
