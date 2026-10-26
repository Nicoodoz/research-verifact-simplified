# 072 执行入口

[执行前协议](protocol.md)固定患者隔离、首轮四臂、统一评价与确认准则。`inspect_candidates072.py`、`review_pool072.py`为离线示例来源审阅；`prepare072.py`只适用于空输出目录，并冻结[首阶段](../../outputs/072_adaptive_judge_examples/freeze.json)。`verify_inputs072.py`在API前核对来源与请求。

`run072.py`是本任务独立的30元累计上限执行器，保存逐次请求/回执，普通通信故障最多3次并退避、必要时降并发；HTTP200结构无效不重试。`analyze072.py`仅在完整同ID答案后调用统一评价。首阶段结束后先写[自适应选择记录](../../outputs/072_adaptive_judge_examples/pilot_decision.md)，`prepare_confirmation072.py`只从盲目标产生唯一候选D4的确认请求；`verify_confirmation_inputs072.py`核对确认冻结。

`review_cases072.py`、`same_body_sensitivity072.py`、`anchor_compare072.py`、`cost_summary072.py`、`verify072.py`均为离线分析/自检。最终结论见[中文总报告](../../outputs/072_adaptive_judge_examples/report.md)。072已结项，不直接再次运行付费执行器，不自动073。
