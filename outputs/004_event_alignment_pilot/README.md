# 004_event_alignment_pilot：结果入口

**已完成，修订定向独立复核 PASS，可正式冻结／结项（2026-09-14）。** 两项原审计问题均已关闭，见 [审计末尾结论](../../reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)。请优先阅读唯一 [中文主报告](run_003/analysis/report.md)。它及旧 status.json／verification 保留生成时的待审计措辞，当前状态以本入口和审计追加结论为准。冻结的科研结果仍来自 run_003，属于 6 名 development 患者的探索性 pilot，不是独立测试成绩；最终论文方法和贡献点仍未确定。

1,263 个逻辑请求均已处理：structured/event_alignment 各 421 个有效预测；routine 有 420 个有效预测和 1 个截断失败。失败原样保留，未补标签或因答案重跑。核心配对仍为完整 LLM 181 / human 240 条，MCC 差值为 +0.0425 / -0.0416，两个患者 bootstrap 区间均跨 0；检查结构遵守有限，不建议直接扩大当前版本。

| 资料 | 入口 |
| --- | --- |
| 独立修订复核 | [结论](../../reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14) · [独立验证证据](../../reviews/artifacts/004_revision_20260914/evidence.json) |
| 执行者修订、自查与交审版本（历史） | [修订说明](verification_live/run_002/README.md) · [verification.json](verification_live/run_002/verification.json) · [review_version.json](verification_live/run_002/review_version.json) |
| 修正后的本地重放 | [replay](verification_live/run_002/replay/) · [费用来源绑定](../../tasks/004_event_alignment_pilot/replay_bindings.json) |
| 用户主报告 | [report.md](run_003/analysis/report.md) |
| 设计、服务参数与运行命令 | [任务说明](../../tasks/004_event_alignment_pilot/README.md) · [真实运行前协议](../../tasks/004_event_alignment_pilot/live_protocol.md) |
| 调用前冻结的输入、配置、代码哈希 | [manifest](run_003/manifest.json) · [preflight](run_003/preflight.json) · [config](run_003/config.json) |
| 完整原生请求与顺序 | [requests.jsonl.gz](run_003/requests.jsonl.gz) · [request_schedule.csv](run_003/request_schedule.csv) |
| 所有开始记录与 1,803 次服务尝试回执 | [attempt_starts.jsonl](run_003/attempt_starts.jsonl) · [receipts](run_003/receipts/) |
| 余额中断后仅恢复无答案请求 | [balance_recovery.json](run_003/balance_recovery.json) |
| 有效性、失败清单及分析范围 | [response_checks](run_003/analysis/response_checks.json) · [analysis_scope](run_003/analysis/analysis_scope.json) · [status](run_003/analysis/status.json) |
| 三臂标签（失败保留空 verdict 与失败状态） | [routine](run_003/analysis/predictions_routine.csv) · [structured](run_003/analysis/predictions_structured.csv) · [event_alignment](run_003/analysis/predictions_event_alignment.csv) |
| 002 统一评价与配对差值 | [metrics.json](run_003/analysis/metrics.json) · [metric_summary.csv](run_003/analysis/metric_summary.csv) · [contrasts.csv](run_003/analysis/contrasts.csv) |
| 患者影响与可回查标签变化 | [robustness.json](run_003/analysis/robustness.json) · [changed_predictions.csv](run_003/analysis/changed_predictions.csv) |
| 实际预算、计费估算与输出遵守 | [usage.json](run_003/analysis/usage.json) · [attempts.csv](run_003/analysis/attempts.csv) · [adherence.json](run_003/analysis/adherence.json) |
| 分析文件及源回执哈希 | [analysis manifest](run_003/analysis/manifest.json) |
| 22 次纯虚构真实 API 测试 | [首个探针](api_preflight/run_001/) · [21 次三臂测试](api_preflight/run_002/summary.json) |
| 本地回放、测试、密钥排查（执行者自查） | [verification.json](verification_live/run_001/verification.json) · [测试日志](verification_live/run_001/tests.log) |

实际 Judge 为硅基流动（SiliconFlow）官方 `deepseek-ai/DeepSeek-V4-Flash`；AWS Bedrock / Groq 已放弃。temperature=0、thinking=false、max_tokens=2048。共 1,263 个模型响应及 540 个无答案余额错误；用户充值后按相同请求补齐。真实推理费用按公开日期公告/usage 估算约 ¥30.326，虚构测试约 ¥0.1744；用户反馈本轮消耗约 30 元额度（16 元优惠券＋14 元充值）；该反馈与 usage 估算分别保留，尚未逐笔核对账单，官网价格差异也未消除。后续实验须控制 token 与调用成本。密钥不进入任何代码、日志或实验产物。

原离线全三臂评分会因一个失败阻止所有比较；本轮明确记录了事后采用逐作者、逐臂/配对完整评价的处理。LLM routine 及涉及它的比较不评分，核心 structured/event_alignment 不删样本并使用原 002 代码。时间冲突患者 98790 的 77 条主分析保留，预设敏感性分析三臂共同排除。

历史 `run_001` 是正式离线准备，`run_002` 是逐字相同的重复准备，均未改写；旧准备报告、synthetic、verification_001 和 verification_live/run_001 保留原历史状态。执行修订新建的 verification_live/run_002 保留交审时状态，只有已有回执的离线验证，没有新增服务请求或补标签。随后独立复核运行 81 项现有测试、41 项隔离篡改检查和两次重放，15 个结果文件均与原结果逐字节一致。001–003 未重新全面审计，原始数据、患者划分和历史实验产物保持不变，独立审计仅追加新结论；reserved test 继续与方法开发隔离。今后交办任务的新增收费调用（含虚构 API 测试和必要补跑）按 [当前 API 费用规则](../../AGENTS.md#api-调用费用与确认规则)：任务预估总费用不超过 40 元可直接执行，超过则先确认；历史授权与预算保留原记录。
