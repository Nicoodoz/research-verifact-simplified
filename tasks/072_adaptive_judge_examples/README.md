# 072 执行入口

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/072_adaptive_judge_examples/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

[执行前协议](protocol.md)固定患者隔离、首轮四臂、统一评价与确认准则。`inspect_candidates072.py`、`review_pool072.py`为离线示例来源审阅；`prepare072.py`只适用于空输出目录，并冻结[首阶段](../../outputs/072_adaptive_judge_examples/freeze.json)。`verify_inputs072.py`在API前核对来源与请求。

`run072.py`是本任务独立的30元累计上限执行器，保存逐次请求/回执，普通通信故障最多3次并退避、必要时降并发；HTTP200结构无效不重试。`analyze072.py`仅在完整同ID答案后调用统一评价。首阶段结束后先写[自适应选择记录](../../outputs/072_adaptive_judge_examples/pilot_decision.md)，`prepare_confirmation072.py`只从盲目标产生唯一候选D4的确认请求；`verify_confirmation_inputs072.py`核对确认冻结。

`review_cases072.py`、`same_body_sensitivity072.py`、`anchor_compare072.py`、`cost_summary072.py`、`verify072.py`均为离线分析/自检。最终结论见[中文总报告](../../outputs/072_adaptive_judge_examples/report.md)。072已结项，不直接再次运行付费执行器，不自动073。
