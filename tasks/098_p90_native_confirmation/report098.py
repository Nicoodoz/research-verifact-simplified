"""Concise Chinese report from locked analyses, without clinical source text."""
import common098 as c

NAMES={'Original':'作者历史R1发布预测','O':'O：发布reference，无示例','C':'C：C48，无示例','P':'P：O＋冻结P90','Q':'Q：O＋等预算普通压缩','F':'F：O＋完整四例'}

def table(tables):
    out=['|配置|MCC|PA|正确数|错误支持/non-S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for m,t in tables.items():
        recall='/'.join('—' if t['per_class'][x]['recall'] is None else f"{t['per_class'][x]['recall']:.1%}" for x in c.LABELS)
        out.append(f"|{NAMES[m]}|{t['mcc']:.4f}|{t['percent_agreement']:.2%}|{t['correct']}/{t['n']}|{t['false_S']}/{t['true_non_S']}|{t['Macro_F1']:.4f}|{recall}|")
    return '\n'.join(out)

def pairtable(pairs):
    out=['|候选−参照|救回/伤害/净正确|ΔMCC及95%患者区间|ΔPA百分点及区间|false-S增加/避免|','|---|---:|---|---|---:|']
    for name,p in pairs.items():
        m=p['paired']['metrics']['mcc'];pa=p['paired']['metrics']['percent_agreement']
        out.append(f"|{p['candidate']}−{p['base']}|{p['rescue']}/{p['harm']}/{p['net']:+d}|{m['delta']:+.4f} [{m['ci95'][0]:+.4f},{m['ci95'][1]:+.4f}]|{pa['delta']*100:+.2f} [{pa['ci95'][0]*100:+.2f},{pa['ci95'][1]*100:+.2f}]|{p['false_S_added']}/{p['false_S_prevented']}|")
    return '\n'.join(out)

def main():
    a=c.read(c.OUT/'analysis.json');cost=c.read(c.OUT/'cost_ledger.json');freeze=c.read(c.OUT/'execution_freeze.json');d=a['decision'];demo=c.read(c.OUT/'demonstration_audit.json');usage=c.read(c.OUT/'usage_summary.json')
    status='继续冻结候选的独立确认' if d['continue_candidate'] else '停止本版本，不扩大、不升级默认'
    natural=a['panels']['natural'];pressure=a['panels']['pressure'];st=a['stability']
    paragraphs=[f'# 098：P90接简洁Judge的同模型确认\n\n**研究建议：{status}。**',
      '研究只评价deepseek-v4-flash-0731简洁Judge的直接verdict，没有分数修正或PriorG。O准确称原作者式适配；未复现原作者辅助格式整理链。作者历史R1预测仅作历史参照。',
      '## 实际范围与冻结\n\n自然400条O/C/P/Q、额外NS/NA各50条O/P、自然事前hash80条补F、60条四臂完全相同body重复，共2120次目标请求，另2次Q构造。最终规模在任何目标回答前按保守目录价及实际材料长度从500缩至400；首8例32次请求忙时，其余闲时，未按首批成绩决定扩量。方法、样本、判定标准见[协议](../../tasks/098_p90_native_confirmation/protocol.md)、[冻结](execution_freeze.json)和[预算计划](budget_plan.json)。',
      f"样本全部来自历史reserved_test40患者，且与登记的示例身份/开发患者隔离。自然GT S/NS/NA={freeze['natural_GT'].get('Supported',0)}/{freeze['natural_GT'].get('Not Supported',0)}/{freeze['natural_GT'].get('Not Addressed',0)}，human/LLM={freeze['natural_author'].get('human',0)}/{freeze['natural_author'].get('llm',0)}。100患者均已有研究暴露，036/092/095等使用过这些资料，不能称未接触holdout或外部测试。自然按GT×作者比例和固定ID哈希抽样，GT只用于抽样与评价。压力面板单独报告，不拼总体PA。",
      '## 示例操作与可识别范围\n\nP逐字复用090最后冻结的四例，不重构、不重选。Q只见相同示例claim、完整源单元和P长度标量，两个长槽各一次独立普通相关性评分，再在匹配预算的完整原文单元子集中按相关性选取；不读取P保护信息组、目标确认标签或历史对错。P/Q/F身份、claim、S/NS/S/NA顺序和呈现模板一致，目标发布reference不变。',
      '|槽|P字符/代理token|Q字符/代理token|P/Q原文相同|\n|---|---:|---:|---|\n'+'\n'.join(f"|{s['ordinal']}|{s['P_chars']}/{s['P_proxy_tokens']}|{s['Q_chars']}/{s['Q_proxy_tokens']}|{'是' if s['same_as_P'] else '否'}|" for s in demo['slots']),
      '普通相关性选择在NS槽自然选到了与P相同的原文；两个短S槽本来原样保留。因此P/Q的真实差异仅在NA长槽，不能将结果扩展为所有示例或通用压缩算法的保护机制。NA槽Q字符多0.44%、代理token少1.05%；代理token不是供应商token，实际usage另列。来源可回查不等于医学充分性认证。',
      f"## 自然主结果\n\n冻结400条，共同有效{natural['common_N']}条、{natural['patients']}人。只用同ID共同有效计算主表，各臂完整覆盖与无效另列analysis.json；没有补NA、旧答案或挑选重复回答。\n\n"+table(natural['tables']),
      pairtable(natural['paired']),
      '预先继续规则要求P同时胜O和Q：MCC至少+0.02、PA下降不超过1个百分点、false-S/non-S增加不超过2个百分点，NS/NA召回各下降不超过5个百分点，并满足MCC区间下界>0或预设的显著风险取舍点值。完整逐项判定见[decision.json](decision.json)，不因结果重改门槛。只赢O不构成保护机制成立；P−C同门槛决定是否值得替代更便宜C。',
      f"P相对O/Q/C的全部门槛是否通过：{d['gates']['O']['pass_all']}/{d['gates']['Q']['pass_all']}/{d['gates']['C']['pass_all']}。是否建议P替代C：{d['recommend_replace_C']}。",
      '## 少数类压力、完整四例及同体波动\n\n压力NS/NA各50条，没有GT=S，S召回不适用；固定三类Macro-F1仍含零支持S类，不与自然面板Macro-F1直接拼接。\n\n'+table(pressure['tables'])+'\n\n'+pairtable(pressure['paired']),
      'F只在事前固定的80条比较，不将其成绩直接与400条相减：\n\n'+table(a['F_diagnostic']['tables'])+'\n\n'+pairtable(a['F_diagnostic']['paired']),
      f"四臂重复冻结60条，共同有效{st['common_N']}条。O/C/P/Q标签翻转分别为{st['flips']['O']}/{st['flips']['C']}/{st['flips']['P']}/{st['flips']['Q']}条。第二次回答不替换第一次，也不按对错择优。首次与重复配对结果均保留：\n\n首次：\n\n"+pairtable(st['first_pairs'])+'\n\n重复：\n\n'+pairtable(st['second_pairs']),
      '## 成本、效率与复核\n\n下表仅比较相同400个自然ID的首次请求，不把P的额外压力样本或F的80条样本混进均值。\n\n|臂|平均输入token|平均输出token|实际每例元|统一闲时无缓存每例元|平均请求秒|\n|---|---:|---:|---:|---:|---:|\n'+'\n'.join(f"|{arm}|{u['mean_input']:.1f}|{u['mean_output']:.1f}|{u['mean_actual_or_reserved_cny']:.6f}|{u['mean_idle_no_cache_cny']:.6f}|{u['mean_seconds']:.2f}|" for arm,u in usage['natural_primary_same_ID'].items()),
      'F的成本仅与同80个ID比较：\n\n|臂|平均输入token|平均输出token|统一闲时无缓存每例元|\n|---|---:|---:|---:|\n'+'\n'.join(f"|{arm}|{u['mean_input']:.1f}|{u['mean_output']:.1f}|{u['mean_idle_no_cache_cny']:.6f}|" for arm,u in usage['F_subset_same_ID'].items()),
      '实际缓存命中受本轮多臂/重复调用影响，不能把某臂实际缓存均值当作独立部署的保证。统一闲时无缓存费用仅用相同病例实际token做可比估计，不是新收费。P90构造复用了已付的090材料，历史构造费用不等于0；Q的本轮构造已完整计入总账，不反向改写历史成本。',
      f"全任务新增{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200，重试{cost['retries']}次；未优惠目录价及未知预留合计¥{cost['used_or_reserved_cny']:.6f}/50，其中未知/未核实预留¥{cost['unknown_or_unverified_reservation_cny']:.6f}。按每次原生usage及峰谷时段核算，不是账户实扣账单；构造和重复都在同一任务账，不以缓存或赠金扩大预算。[逐尝试账](attempt_ledger.jsonl)、[总账](cost_ledger.json)、[本次核价](../../tasks/098_p90_native_confirmation/pricing_verification.md)。",
      '主要PA/MCC/AC1调用仓库evaluate和paired_compare，1000次患者cluster bootstrap；独立混淆矩阵算式与sklearn复核。完整每类P/R/F1、混淆矩阵、false-S/non-S、预测S假发现率、human/LLM分层、救回/伤害ID及覆盖见[analysis.json](analysis.json)、[逐条预测](predictions.jsonl)、[主表CSV](main_table.csv)。自检见[selfcheck.json](selfcheck.json)，属于执行者自检，独立审计未执行。',
      '区间条件于固定预测与既有暴露患者，不覆盖历史开发选择、重训、服务变化或新医院泛化。当前服务返回同一0731标识并采用同设置，不能据此证明与历史平台逐字节科学等价；本轮各臂同期交错比较避免依赖该等价假设。原医生GT基于完整EHR，reference只是模型实际输入；理由/引用没有当作新医生gold或内部推理证明。O/C改变了证据内容与长度，不能称等信息量；本轮仍只评价医生标注的原子命题，不证明整篇临床文档拆分及核验流程已经有效。',
      f"## 研究决定\n\n{status}。本任务不更换示例、不调新阈值、不拟合后处理、不自动开展099；默认C48→V4 T-S无示例B→Frozen PriorG保持不变。所有成果保留本地，未提交或推送。"]
    text='\n\n'.join(paragraphs)+'\n'
    p=c.OUT/'report.md'
    if p.exists():assert p.read_text(encoding='utf-8')==text
    else:p.write_bytes(text.encode('utf-8'))
    print(status)

if __name__=='__main__':main()
