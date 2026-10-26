# 081 GT-blind evidence selection

本任务在同一24名development患者的96条valid claim上比较原包 B、GT盲选证 U、仅多医生GT的教师 T。冻结C48、DeepSeek 0731 T-S及053 Frozen PriorG；费用硬上限¥20。详见[事前协议](protocol.md)与[输出入口](../../outputs/081_gt_blind_evidence_selection/README.md)。

实施顺序：`prepare_blind081.py`冻结患者内哈希抽样 → `stage_u081.py`冻结并运行U planner/composer与最终pack → `stage_t081.py`读取GT并构建T和交错B/U/T Judge → `analyze081.py`统一评价 → `verify081.py`来源与泄漏顺序自检。`run081.py`逐请求落盘、累计限额、有限恢复，成功回答不可重发。运行环境入口是`scripts/run_research.ps1`。

Stage 2 的96条备用ID在初次样本冻结时确定；只有事前gate与完整剩余预算同时允许才执行。所有输出保存在独立081目录，不覆盖历史任务。执行者自检不等于独立审计。
