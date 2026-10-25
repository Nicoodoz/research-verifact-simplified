# 046 当前状态

046第一批六路检索/证据呈现筛选已完成；按协议停止，不自动扩大。执行者核验PASS；独立审计未执行。

队列：16条development诊断病例，8名患者，reserved overlap=0。
- retrieval-sensitive 6；
- judge-error control 2；
- protection 8。

raw DeepSeek结果：
- Base 8/16。
- R1 自由语义补证：9/16，2 rescue / 1 harm。
- R2 requirement-aware：9/16，2 / 1。
- R3 R1证据短原文窗：10/16，**2 / 0**。
- R4 关系集合：9/16，1 / 0。
- R5 局部上下文恢复：9/16，2 / 1；与R1标签完全相同。
- R6 缺口扩检＋语义重排：8/16，1 / 1。

4条base同输入repeat全部稳定。

关键机制回查：
- R3/R1两个主要rescue的关键事实原本已经在E0，不能称为missing-evidence recovery；更像证据聚焦/注意力重分配。
- R3相对R1唯一标签差异是避免了“last chemotherapy course in September”保护样本的NA→NS harm；整段R1加入了相关但不能回答September限定的治疗背景，短窗没有。
- R2独有rescue和R6独有rescue都不是“新增原文直接解决核心claim”的干净例子。

第一批决策：
- R3作为 evidence focusing 候选保留。
- R1/R2/R4/R5/R6当前版本不扩大。
- 当前尚未筛出一个可称为true missing-evidence retrieval winner。
- 下一步若继续retrieval主线，应先构建development上的true missing-evidence机制集：明确目标信息不在E0、但存在于D48或eligible EHR。

执行：
- 118/118 HTTP200；
- parser 117 valid，1个R1 selector截断JSON保留invalid、不重跑；
- Qwen 69次，DeepSeek 49次；
- usage估算费用 **¥2.244342 / ¥8**。

入口：report.md · analysis_summary.json · route_summary.csv · transitions.csv · verification_001.json
