# 002_reproduce_paper_results：独立审计记录

**总体结论：通过，可进入后续研究。统一评价与发布预测的重评分可信，但不等于全部论文结果均已复现。**

本记录于 2026-09-13 补记，包含此前审计及随后对 human-written claim MCC 的核实；未重新开展审计。

## 对象与实际审查范围

审查 [002 评价协议](../tasks/002_reproduce_paper_results/README.md)、[正式 run_003 报告](../outputs/002_reproduce_paper_results/run_003/report.md)、统一评价实现、公共 CLI、论文对照和作者代码。覆盖 human ground truth 与发布 VeriFact 预测的 PA（Agreement）、AC1、MCC、混淆矩阵，以及不同模型、Top-N 和 fact type。

当时 30 项测试通过；独立完整重跑的 37 个机器结果文件与正式 run_003 一致。另用独立库核验全部 426 个配置的指标与混淆矩阵，并检查队列、非法输入拦截、实际患者 bootstrap 抽样及不同模型的配对比较；未发现影响已报告指标的实现错误，原始数据未改变。

## 核心判断与问题状态

- **必须修正的问题：无阻塞项。** 正文默认 R1-70B + 100 sentence facts 在 LLM claim 的 all-propositions 队列（n=3,447）得到 PA 93.1535%、MCC 0.309543，支持正文展示的 93.2%、0.31。该配置在所核验的 126 个 LLM claim 主配置中 MCC 最高；“最佳”不能解释为 Agreement 也最高。研究默认 valid-only（n=3,441）的 MCC 为 0.305697，两套口径须分开。
- **论文差异：保留为非阻塞限制。** 论文 MCC 区间为 [0.24, 0.35]，复算 item bootstrap 约为 [0.245125, 0.366813]，未完全复现；部分正文模型增益也有显示数值差异，原因未确认。正式补充附录未取得，不能声称完成全部附录数值核验。
- **非阻塞代码问题：外部输出目录。** 当时复现脚本使用仓库外 `--output-root` 会在 `run.relative_to(ROOT)` 处抛出 `ValueError`；默认仓库内运行和公共评价 CLI 不受此问题影响。建议修正路径展示逻辑；本会话没有完成其修正后的复核，不能记为已解决。
- **human-written claim 的 0.478 已核实。** 同一 baseline 在 valid-only human claim（n=5,624）上的 MCC 为 0.478276；all-propositions（n=5,648）为 0.476735。这是正确的发布数据重评分结果，未确认与正式论文附录对应数值一致，也不能与 LLM claim 的 0.31 当作同一队列成绩比较。

## 最终建议

接受 run_003 和统一评价模块作为后续研究基础。新方法与 baseline 应在同一实际队列上调用同一评价入口，并使用配对比较；不能拿论文抄录的 0.31 直接对比另一队列的新方法结果。

本任务重评的是作者发布预测，没有重新运行原作者模型；全量 benchmark 成绩也不是新方法的独立测试成绩。后续开发前必须冻结患者划分。版本定位采用 [run_003 manifest](../outputs/002_reproduce_paper_results/run_003/manifest.json)，不推定未能确定的审计时 Git commit。

## 后续状态同步（2026-09-13）

上述建议中的患者划分已在 003 冻结：20 名探索、40 名开发、40 名保留测试，见 [冻结清单](../outputs/003_error_analysis/patient_groups.json) 及 [003 结果入口](../outputs/003_error_analysis/README.md)。003 已完成修订自查，用户已确认结项。后续新方法及 baseline 应按同一冻结分组、实际队列和公共评价入口比较；全量 benchmark 仍不能充当独立测试成绩。

本次文档同步核对发现，仓库外 `--output-root` 的路径展示错误仍在，未修复；已在 [002 运行说明](../tasks/002_reproduce_paper_results/README.md) 中明确使用限制。其余原审计结论和历史验证记录保持不变。
