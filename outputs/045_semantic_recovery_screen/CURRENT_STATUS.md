# 045 当前状态

045第一批路线筛选执行完成；按协议停止，不自动进入第二批。执行者核验PASS_WITH_D_CITATION_FORMAT_WARNING；独立审计未执行。

16条development诊断集，7名已使用患者，reserved overlap=0；8条base错误 + 8条正确保护对照。

路线结果（raw verdict）：
- Base：8/16正确。
- A 改DeepSeek核验范围：8/16，0 rescue / 0 harm。
- B Qwen语义选证→DeepSeek：8/16，0 / 0；Qwen 15/16选none。
- C DeepSeek反馈→Qwen查询→本地BM25→DeepSeek：8/16，0 / 0；7条实际补检，但raw标签均未改善。
- D Qwen直接Judge：10/16，**2 rescue / 0 harm**，false-S不增加。

D两个rescue的关键依据本来就在原C48：
1. hct下降→possible GIB：原C48明确写first consideration/concern为GIB。
2. 2-3 repeat speech/swallow：原C48明确写同日refused speech and swallow；Qwen正确判NS，DeepSeek判NA。

4条原DeepSeek同输入repeat全部不变。

费用：76次新API调用，76/76 HTTP200，usage估算 **¥0.993993 / ¥8**。

结论：A/B/C当前版本淘汰；D保留进入下一批小样本确认。当前新线索更偏向evidence-present-but-misinterpreted：模态、事件完成状态与NS/NA边界，而不只是检索召回。

限制：D的checks.evidence_ids使用Note ID字符串而非编号reference ID，引用格式不合规；下一批若继续D必须先修schema。固定λ=2不应直接用于Qwen分数作正式评价。

入口：report.md · analysis_summary.json · changed_cases.csv · verification_001.json
