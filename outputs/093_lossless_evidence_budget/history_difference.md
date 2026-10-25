# 093 历史核对与实际区别

基准HEAD e3999daa6。以下依据正式报告、协议及关键实现，不把旧负结果外推为整条方向不可能，也不以换模型设置或样本大小制造“新机制”。

|拟议操作|最接近旧实验及实际执行|本轮实际区别|是否值得新测|
|---|---|---|---|
|命题要求→关系→引用→全部支持放S|028真实155候选×trace/repeat；相对SD净−40，true-S救回保留44/110；引用格式也有失败，但不是唯一失败原因|没有新信息，换成证书或checklist仍相同|不新测|
|覆盖/多样性重排和打包|042固定D48/8000字符；240条B/SoftNote/CovMMR U2正确205/203/205，确认696未运行|仅换覆盖权重或同note上限没有实质区别|不新测|
|要求感知补证、关系集合、缺口扩检|046六路16条真实；R3短窗2救回/0伤害，但关键事实原在E0；R4仅1/0，R5与R1同标签，R6 1/1|不能把要求/事件关系字段重新命名为新图结构|不新测|
|逐要求查证后扩大EHR搜索|048系统冲突触发16条；K/G raw都3/16，原B2/16，raw仅同一患者1救回；确认29未运行|更大的pool/更多查询或thinking开关不构成新机制|不新测|
|恢复切割边界、标题、相邻上下文|011已实现同段边界及局部标题；24条三臂三轮，无稳定净收益；650主实验未执行。046 R5也追加相邻span|不是历史未实现的新操作|不新测|
|原证据重排/短窗呈现|047患者分离screen24：P只重排净−1，S选短窗净0；确认64未运行|只重排序或称“聚焦”会重叠|不新测|
|明确反证否决或把关系表交给Judge|049规则与真实screen均损失真S；打乱requirement↔quote配对0/5标签差异|不是给已有Gate换名即可获得关系作用|不新测|
|根据下游效用删/增/替换|069同一操作稳定救回仅2/1/1，GT盲第二步未运行；081完整GT盲/教师选包与重复未证明稳定增量|不能将oracle或不稳定评分监督拿来训练同类selector|不新测|
|精确重复原文共享→只用省下的预算补候选|042最接近，但它为新片段可能挤出旧片段；046/048多为额外追加。090研究示例抽取而非目标C48|原包可机械展开回原字节，所有来源/日期/出现位置保留；新段仅来自原D48与原排序，不增加字符预算；F控制呈现效应，A−F检查补证增量|结构盘点后可测，执行唯一版本|

## 依据与实现层核对

- 028 common028.py的TRACE_INSTRUCTION明确包含动态material requirements、supported/contradicted/unaddressed/uncertain、claim/evidence逐字引用及覆盖；其放行规则是候选流程，不是独立三分类升级。[报告](../028_traceable_claim_evidence_verification/report.md)。
- 042 common042.py/prepare042.py确认相同48候选、原分数、cap8000、max_items16、原每note2；CovMMR固定70/20/10相关性/覆盖/新颖性并软罚重复note。[报告](../042_coverage_aware_evidence_packing/report.md)。
- 046 prepare046.py/build_final046.py确认R4实际选互补关系集合、R6缺口查询；R3保留原E0另加短原文，R5真实相邻span恢复。[协议](../../tasks/046_requirement_aware_retrieval_screen/protocol.md)、[报告](../046_requirement_aware_retrieval_screen/report.md)。
- 048 common048.py/build_screen_audits048.py/build_screen_finals048.py确认claim-only要求/查询、D48或full eligible corpus、top32检索、逐quote校验、最多12段追加原文；生成关系没有直接混入最终EHR。[协议](../../tasks/048_end_to_end_evidence_recovery/protocol.md)、[报告](../048_end_to_end_evidence_recovery/report.md)。
- 011 packaging011.py已经做repair_span和enclosing_local_heading，不能声称源码从未实现结构恢复。[成果](../011_evidence_integrity_packaging/README.md)。
- [049](../049_evidence_decision_utilization/report.md)、[047](../047_mechanism_stratified_validation/report.md)、[069](../069_final_pack_controlled_repair/report.md)、[081](../081_gt_blind_evidence_selection/report.md)分别约束关系直接决策、呈现、受控修复及utility选择的主张。067来源冲突沿[069更正](../069_final_pack_controlled_repair/067_correction.md)，不能用其旧v1成绩佐证新方法。
- 090构造曾修复接口并实际得到压缩方案，不能说示例压缩从未测到；091的选择性核验原型因材料不足未分类实测；092实际更新encoder且完成全量OOF，本轮不延伸该路线。

## 选中候选的限度

本轮新的是“保留全部原包内容与来源，用确切节省的预算加入原候选”的可执行约束，而不是字典共享、检索或压缩算法首创。文本完全相同不能证明笔记互相复制、事件相同或证据不独立；本轮不利用这些未经证实的医学假设改变标签。没有保证折叠呈现易被Judge使用，因此保留只折叠F对照。

额外原文可能帮助真S及NS/NA分类，不能只观察false-S减少；沿同一Frozen PriorG评价并单列raw→final覆盖/反转。没有对主Judge微调、加F4、训练辅助组件或重新拟合后处理。
