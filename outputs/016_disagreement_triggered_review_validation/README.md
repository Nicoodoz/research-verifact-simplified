# 016成果入口

**第一阶段因服务失败导致费用重估超40元而停止，实验未完成，未判断方法效果。唯一必读：[中文主报告](report.md)。** 已收246份有效基础回答（V4 122、Qwen124），累计usage估算及未知预留¥5.81291603。无分歧复核或后续阶段，待独立审计。

- [当前事前协议](protocol_002.md)：全量V4/Qwen，分歧上普通重复与独立review，门槛及停止条件。
- `stage1/`：第25–30名六开发患者601条；正式原始准备为preparation_002。
- `live/`：全任务统一预算台账与各阶段原生回执。
- `interruption_001/`：停止依据、原台账快照、单独对账副本、部分预测及费用；原live不回写。
- [停止状态自查](interruption_verification_002/summary.json) · [交审说明](audit_handoff.md)。`task_api.lock`保留为停止锁，不代表客户端仍在运行，不得误删续跑。
- `authority_001.json`、`prices_001.json`、`token_calibration_001.json`、`budget_checks/`：40元授权来源、实时价核验、历史usage校准与发送前实际body估算。
- `protocol_001.md`、`budget_request_001.json`、`precharge_history_001/`及`stage1/preparation_001/`：用户缩减前的无收费历史预案，不再执行；对应源文件快照可核验旧manifest，不能拿当前源码假装旧版未变。

014/015当前已独立审计PASS，原结果/协议偏差及015停止决定保留；016是用户新交办的独立假设检验。
