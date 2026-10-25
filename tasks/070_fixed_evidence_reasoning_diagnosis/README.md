# 070：固定证据下的 LLM 判断差异诊断

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/070_fixed_evidence_reasoning_diagnosis/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

本任务依据[零 API 分析协议](protocol.md)复用 050–053、055、066、068–069 的同证据回答与重复回执，并核查 066 Reasoning Oracle 可修复的 14 个错误及其完整队列代价。[中文报告](../../outputs/070_fixed_evidence_reasoning_diagnosis/report.md)、[逐例台账](../../outputs/070_fixed_evidence_reasoning_diagnosis/case_ledger.md)、[自检](../../outputs/070_fixed_evidence_reasoning_diagnosis/verification.json)为结果入口。

离线重放：

```powershell
pwsh -File scripts/run_research.ps1 tasks/070_fixed_evidence_reasoning_diagnosis/analyze070.py
python tasks/070_fixed_evidence_reasoning_diagnosis/build_casebook070.py
python tasks/070_fixed_evidence_reasoning_diagnosis/verify070.py
```

不开发 prompt、模型路由或后处理，不自动启动 071。`inspect_casebook070.py` 和 `reference_spots070.py` 仅打印完整证据与输出供人工核对。
