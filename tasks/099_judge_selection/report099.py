"""Chinese outcome report and a small, separately authorized future deployment bridge."""
import common099 as c

def table(tables):
    order=['Original']+[m for m in c.MODELS if m in tables]
    out=['|配置|MCC|PA|正确数|错误支持/non-S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for m in order:
        t=tables[m];rec='/'.join('—' if t['per_class'][lab]['recall'] is None else f"{t['per_class'][lab]['recall']:.1%}" for lab in c.LABELS)
        out.append(f"|{m}|{t['mcc']:.4f}|{t['percent_agreement']:.2%}|{t['correct']}/{t['n']}|{t['false_S']}/{t['true_non_S']}|{t['Macro_F1']:.4f}|{rec}|")
    return '\n'.join(out)

def pairs(pp,contextual=False):
    out=['|候选−参照|救回/伤害/净正确|ΔMCC [95%患者区间]|ΔPA百分点 [区间]|false-S新增/避免|','|---|---:|---|---|---:|']
    for key,p in pp.items():
        m=p['paired']['metrics']['mcc'];a=p['paired']['metrics']['percent_agreement']
        label=f"{key}：{p['candidate']}−{p['base']}" if contextual else f"{p['candidate']}−{p['base']}"
        out.append(f"|{label}|{p['rescue']}/{p['harm']}/{p['net']:+d}|{m['delta']:+.4f} [{m['ci95'][0]:+.4f},{m['ci95'][1]:+.4f}]|{a['delta']*100:+.2f} [{a['ci95'][0]*100:+.2f},{a['ci95'][1]*100:+.2f}]|{p['false_S_added']}/{p['false_S_prevented']}|")
    return '\n'.join(out)

def main():
    a=c.read(c.OUT/'analysis.json');s=a['selection'];cost=c.read(c.OUT/'cost_ledger.json');f=c.read(c.OUT/'execution_freeze.json');meta=c.read(c.OUT/'model_metadata.json');primary=s['primary'];backup=s['backup']
    O=a['O_natural'];diag=a['diagnostic'];C=a['C_subset'];strict=a['strict_format_sensitivity'];st=a['stability']
    head=f"**主候选：{primary}；备选：{backup}。** 原系统发布reference下API点估计领先者为{s['API_point_leader']}。"
    if s['primary_is_conditional']:head+='没有可部署候选完整达到预设底线，主候选只是有条件的后续验证对象，不推荐默认升级。'
    else:head+='这是固定低成本配置、小型已暴露面板上的选型建议，不是已证明全总体模型优劣，也不是API/A800等价结论。'
    lines=['# 099：VeriFact Judge模型选型\n\n'+head,
      '## 完成范围与固定条件\n\n仅当前已授权阿里云/千问AI平台端点，四模型统一097原作者式简洁任务、无示例、无后处理，评价直接verdict。O是发布reference，C是冻结C48。所有模型相同ID及任务，选型先看O，不看哪个模型使C−O更好。[冻结协议](../../tasks/099_judge_selection/protocol.md) · [实际冻结](execution_freeze.json)。',
      f"在目标输出前一次冻结自然{f['chosen']['natural']}条O，其中{f['chosen']['C_subset']}条C；另NS/NA各{f['chosen']['diagnostic_each']}条O，8条O四模型同body重复，共{f['chosen']['jobs']}请求。自然GT S/NS/NA={f['natural_GT']['Supported']}/{f['natural_GT']['Not Supported']}/{f['natural_GT']['Not Addressed']}，human/LLM={f['natural_author']['human']}/{f['natural_author']['llm']}，自然{f['natural_patients']}人、全体{f['patients']}人。自然从097冻结160按GT×作者和固定ID哈希抽样；诊断来自096自然800排除本轮自然ID，未按历史对错筛选。全部患者已有研究暴露，不称新holdout。",
      '统一temperature0、top_p1、thinking开启、thinking_budget2048、最终max_tokens512；未设置reasoning_effort或response_format。Qwen接口max_tokens通常不含思考，所以账本预留思考+最终回答。该配置检验固定资源预算下的Judge，未测试各模型默认最大推理。计划以最大思考/回答和实际输入预测约15.52元而选择80自然，不按先跑成绩扩量；剩余预算不用于挑模型/示例/提示。[预算计划](budget_plan.json)。',
      '首例四模型HTTP200均保留，Flash出现外层Markdown JSON围栏。首次正确率/GT连接前做了四模型共同、确定性的完整外围栏去除，内部仍必须是完整JSON，不补括号、不搜正文标签、不调模型。原严格parser、原始响应与严格敏感性表保留，没有成功回答重发。[工程修正](../../tasks/099_judge_selection/format_amendment.md) · [修正指纹](format_amendment_freeze.json)。',
      '## O：原系统输入下主结果\n\n'+f"冻结{O['frozen_N']}条、四模型共同有效{O['common_N']}条。Original为作者历史R1同ID预测，不是同期API臂。\n\n"+table(O['tables']),
      pairs(O['paired']),
      '|模型|有效/冻结|无效|完整N已知正确下界|\n|---|---:|---:|---:|\n'+'\n'.join(f"|{m}|{O['coverage'][m]['valid']}/{O['coverage'][m]['frozen_N']}|{O['coverage'][m]['invalid']}|{O['coverage'][m]['known_correct']}/{O['coverage'][m]['frozen_N']}|" for m in c.MODELS),
      '097的V4历史简洁任务在当前共同ID上另列analysis.json historical字段；其模型、思考配置、调用时间与本轮不同，只作历史背景，不用来宣称纯模型效果。医生GT面对完整EHR，发布reference也只是当次模型实际输入，不认证为gold evidence。',
      '## 三类诊断、C48迁移与稳定性\n\n额外NS/NA各16条，四模型共同有效'+str(diag['common_N'])+'条，没有GT=S；S召回不适用，三分类Macro-F1含零支持S类，不与自然面板拼接。\n\n'+table(diag['tables']),
      'C48仅在事前32条子集实测；下列两表同一批ID，不将32条与80条正确率直接相减。O/C实际内容与长度不同。\n\nO匹配子集：\n\n'+table(a['O_matched_C_subset']['tables'])+'\n\nC48：\n\n'+table(C['tables']),
      pairs(a['O_to_C'],contextual=True),
      f"8条重复共同有效{st['common_N']}条，四模型标签翻转为"+'、'.join(f"{m} {st['flips'][m]}" for m in c.MODELS)+'。第二次答案不替换首次，不按对错择优；8条只能发现波动，不能精确估计稳定性。原生reason与reasoning_content不当作内部推理或新医生GT。',
      '## 为什么这样推荐\n\n预先底线为O有效覆盖≥95%、PA不比同ID作者低超过5个百分点、诊断NS/NA召回均≥20%；单卡主候选还需可追溯公开权重与合理BF16显存。先按O MCC，再在MCC差≤0.02、PA差≤0.02的实用近邻中限制false-S至多多1条及PA差≤0.01，最后按同ID实际token的无缓存原价和部署余量取舍。没有用C−O改善幅度选择模型。',
      '|候选|质量底线通过|单A800高保真候选|\n|---|---|---|\n'+'\n'.join(f"|{m}|{s['floors'][m]['pass_all']}|{s['floors'][m]['single_A800_high_fidelity']}|" for m in c.MODELS),
      f"可部署MCC点估计领先为{s['MCC_leader_deployable']}；实用近邻为{', '.join(s['practical_nearby']) or '无'}；最终风险/成本近邻为{', '.join(s['risk_cost_nearby']) or '无'}。主候选{primary}，备选{backup}。区间跨0不代表等效，小差值和单个NS病例均不应包装成稳定超越。",
      '本轮有明确代价：35B-A3B的自然NA召回只有2/13（15.4%），作者历史同ID为6/13；其自然MCC虽高于27B，Macro-F1却稍低。额外诊断35B/27B正确17/22、false-S为7/2；因此27B是有实质价值的风险备选。35B在匹配32条接C48后，正确25→22、false-S 1→3。按事前O优先规则仍推荐35B作下一步桥接候选，但没有证据支持它全面更安全；尤其不能把O选型直接当成C48系统默认替换证据。',
      f"严格原parser敏感性：四臂O共同有效仅{strict['O_natural']['common_N']}条，该极小交集上的自动规则给出{strict['selection']['primary']}，与主推荐一致={strict['primary_same']}。Flash严格有效5/80、规范化后79/80；主候选和备选均严格有效80/80，二者自身标签没有因围栏处理改变。严格交集缩小主要是Flash格式造成，五条排序仅作敏感性诊断；完整覆盖、逐条strict标签及小交集自动选择均保留在analysis/predictions。主推荐仍受小样本与已暴露患者限制。",
      '## 价格、精度及单A800部署\n\n|模型|输入/输出原价（元/百万token）|公开BF16权重GB|判断|\n|---|---:|---:|---|\n'+'\n'.join(f"|{m}|{c.PRICES[m][0]}/{c.PRICES[m][1]}|{meta[m]['weight_bytes']/1e9:.2f}|{'完整权重超80GB，需重大改变，API参照' if m=='qwen3.8-flash' else 'BF16单卡候选；尚未部署实测'}|" for m in c.MODELS),
      '公开27B模型约51.75GiB、35B-A3B约66.96GiB权重，加KV、SSM状态和工作区后后者余量更紧；激活3B不等于只加载3B。Flash官方关联Flash-Next约360GB，不能把裁剪或重量化版本当同API的精确等价。优先官方BF16、单并发、text-only和足够覆盖实际输入的context，避免先引入量化变量。[逐模型核对与官方链接](../../tasks/099_judge_selection/model_audit.md)。API实际精度、revision和内部模板未独立核实，全部标unknown；公开权重BF16不证明服务BF16。',
      '## 实际费用\n\n下表仅同80条O首次调用，避免不同面板/重复混入成本对比。无缓存原价是用实际token归一的估算，不是新增费用。\n\n|模型|平均输入token|平均输出（含思考）|实际每例元|无缓存每例元|平均秒|\n|---|---:|---:|---:|---:|---:|\n'+'\n'.join(f"|{m}|{t['mean_input']:.1f}|{t['mean_output']:.1f}|{t['mean_actual_cny']:.6f}|{t['mean_no_cache_cny']:.6f}|{t['mean_seconds']:.2f}|" for m,t in a['cost_natural_O'].items()),
      f"全099累计{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200，重试{cost['retries']}；未优惠目录价及未知预留¥{cost['used_or_reserved_cny']:.6f}/20，未知预留¥{cost['unknown_reservation_cny']:.6f}。此前没有099费用；全部本轮预检、重复、恢复均在同一账内。输出预算包络超限{cost['output_envelope_violations']}次。[总账](cost_ledger.json)、[逐尝试](attempt_ledger.jsonl)、[usage](usage.jsonl)。不是账户实扣账单，未租GPU、未下载权重、未改默认配置或098。",
      '## 后续最小API/A800一致性检查\n\n本轮已在质量结果前冻结[24条桥接ID](future_A800_bridge24.jsonl)，S/NS/NA各8，全部O输入，按哈希和患者分散选择。下一次部署须另获授权；当前只交付[具体方案](A800_bridge_plan.md)，不启动AutoDL或新增桥接API。',
      '## 自检与限制\n\n仓库evaluate/paired_compare及1000次患者cluster bootstrap；另用独立混淆矩阵算式/sklearn及Decimal费用复核，原请求/输入/患者/GT隔离、原冻结/默认与098文件指纹核验见[selfcheck.json](selfcheck.json)。这是执行者自检，独立审计未执行。完整三类P/R/F1、confusion、false-S/non-S及预测S假发现率、human/LLM分层与救回/伤害ID见[analysis.json](analysis.json)、[逐条预测](predictions.jsonl)、[主表CSV](main_table.csv)。',
      '自然只有6条NS，诊断每类16条，患者均已暴露且服务只测一批；本轮适合低成本选型，不能证明稳定全面优越。固定思考预算与格式规范化也限定结论范围。当前仍是医生标注原子命题评价，不是整篇临床文档系统已验证。最终推荐不改默认Judge、不启动下一实验、不commit/push。']
    ctext='\n\n'.join(lines)+'\n';p=c.OUT/'report.md'
    if p.exists():assert p.read_text(encoding='utf-8')==ctext
    else:p.write_bytes(ctext.encode('utf-8'))
    bridge=f'''# 后续API与单A800最小一致性检查（方案，未执行）

建议主模型{primary}，必要备选{backup}。固定ID见future_A800_bridge24.jsonl，24例S/NS/NA各8，选择发生在099质量结果之前，不能换成API/本地更易一致的病例。

1. 用户确认A80080GB实例后，独立新环境固定引擎/torch/CUDA/transformers版本。下载官方checkpoint的精确revision（本轮{primary}为{meta[primary]['revision']}），记录所有权重、tokenizer和chat_template SHA；BF16、TP1、单并发、text-only，不启用量化、投机或MTP，不改旧085/096环境。按24条实际token长度+完整输出余量选max_model_len，不截断或重选长例；无法容纳时先报告该配置的真实部署限制。

2. 从099私有原始job复制完全相同system/user文字，原O/claim SHA逐例核对，GT不进请求。temperature0、top_p1、thinking开启。阿里云thinking_budget2048对应vLLM新版本的thinking_token_budget2048，并启用正确reasoning parser/起止token；不能把参数原样照搬而假定已生效。3.8的low力度/模板设置也需核对。参考[官方thinking budget控制](https://docs.vllm.ai/en/stable/features/reasoning_outputs/)。本地max_tokens通常包含思考，需为2048思考+512回答留足总上限；若无法单独约束最终512，必须标明差异并检查上限是否实际触发，不能声称参数完全等价。记录强制结束思考的token序列；平台内部强制策略未知。

3. 先做2条固定技术检查（计入24），再一次运行其余22。复用099对应API首次答案；如需排除时段漂移，另行授权8条固定hash的同body API桥接，估算按本轮主模型实际token费用×8并预留最大输出，不继承099剩余额度。本地在固定8条上重复一次，比较引擎自身波动，不择优。保存完整生成参数、token计数、结束原因、输入SHA和回执。

4. 主要看24条raw标签一致数/百分比、API→本地三分类转移、invalid、false-S与PA/MCC变化、显存峰值/首token和总时延；同时报告严格及同一外层围栏规范化解析。24条平衡面板不能当自然性能估计。初步工程门槛可设全部有效且至少23/24标签一致；≥2个分歧或任何系统性类别偏移时先定位权重/模板/预算/算子问题，不直接扩大。即使23/24也只是小样本可行性，不是统计等效或跨医院泛化证据。

5. API精确权重revision/精度始终无凭据时保留unknown。BF16仍明显不一致，则如实将API与本地当两个后端，后续同模型公平比较在同一后端内完成，不通过改prompt、选病例或多次重发制造一致。全流程不改变099选型主表与098冻结材料。
'''
    bp=c.OUT/'A800_bridge_plan.md'
    if bp.exists():assert bp.read_text(encoding='utf-8')==bridge
    else:bp.write_bytes(bridge.encode('utf-8'))
    print(c.canonical(dict(primary=primary,backup=backup,conditional=s['primary_is_conditional'],cost_cny=cost['used_or_reserved_cny'])))

if __name__=='__main__':main()
