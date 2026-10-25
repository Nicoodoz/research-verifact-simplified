# 013成果入口

**2026-09-15快速独立审计PASS，可冻结／结项。** 只需阅读[简明中文主报告](report.md)。四个具体方案在固定231条压力集均未通过预设门槛：contract净−12、text_guard−4、wide_candidates−5、selector−5；没有winner、组合或新患者确认。保留C48对照，不追加规则救本轮。

- [事前协议](protocol_001.md)：历史正反结果约束、四个独立分支、固定筛选与确认门槛。
- [固定选样](preparation_001/selection.json)：195错误并集＋36正确对照，LLM71/human160。
- [机制门槛](unit_analysis_001/gate.json)与[完整解释复查](unit_analysis_001/semantic_review.json)：不是泛化成绩。N264保持patient主体后仍与原NS GT不一致；时间/范围问题未被该窄合同解决。
- [费用计划](budget_plan_001.json)与[长期授权登记](authority_001.json)：全任务40元硬上限，初始单位检查预计约0.56元，之后按实际请求及全任务剩余额度核算。最终估算/预留[18.80024461元](synthesis_001/costs.json)。
- [完整评分与转移](screen_analysis_001/summary.json)、[核心表](synthesis_001/results.md)、[停止gate](screen_analysis_001/gate.json)：六条件各231条有效预测，原GT与统一评价不变。
- [现行35例诊断](review_final_002/coverage.json)、[87处引文与解释](review_final_002/notes.json)、[16项真实成员检查](membership_backcheck_001/checks.json)：保留改善、退化及稳定对照；三处初稿入选误读已修正，未改变模型结果。
- [输入诊断002](screen_input_diagnostics_002/summary.json)、[机制追踪](mechanism_analysis_001/raw_traces.json)、[原条件字段回查](mechanism_analysis_001/prefix_scope_backchecks.json)、[事前探针后续](probe_followthrough.md)：程序事实与医学解释分开。
- [174项断网测试与重放](verification_001/verification.json)、[实际交审版本](audit_handoff.md)：001–012的10437文件和25个raw输入不变。
- `live/`：每次实际请求、响应、账号别名、usage/费用和未解决失败；不覆盖回答。

已停止全部收费调用。剩余16名development没有进入新实验，reserved test保持隔离。`precharge_draft_001`、`screen_input_diagnostics_001`、`review_final_001`分别保留预算、rank展示和解释的旧草稿；现行正式输入/评价不变，当前解释以review_final_002及主报告为准。`execution_status.md`是可变工作记录，不是更高优先级的研究结论。

当前独立结论见[013审计](../../reviews/013_multi_mechanism_screen.md)。原报告与交审快照保留其形成时状态，四分支停止、不做组合或新患者确认。

当前项目没有正在等待续跑的013实验，也没有通过压力筛选的新方案。后续建议是先整理001–013证据并重新论证研究问题；最新项目状态见[根README](../../README.md)，本轮结论不等于所有一般研究机制无效。
