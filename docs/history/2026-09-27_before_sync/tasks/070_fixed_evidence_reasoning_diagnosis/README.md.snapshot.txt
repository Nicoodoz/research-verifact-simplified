# 070：固定证据下的 LLM 判断差异诊断

本任务依据[零 API 分析协议](protocol.md)复用 050–053、055、066、068–069 的同证据回答与重复回执，并核查 066 Reasoning Oracle 可修复的 14 个错误及其完整队列代价。[中文报告](../../outputs/070_fixed_evidence_reasoning_diagnosis/report.md)、[逐例台账](../../outputs/070_fixed_evidence_reasoning_diagnosis/case_ledger.md)、[自检](../../outputs/070_fixed_evidence_reasoning_diagnosis/verification.json)为结果入口。

离线重放：

```powershell
pwsh -File scripts/run_research.ps1 tasks/070_fixed_evidence_reasoning_diagnosis/analyze070.py
python tasks/070_fixed_evidence_reasoning_diagnosis/build_casebook070.py
python tasks/070_fixed_evidence_reasoning_diagnosis/verify070.py
```

不开发 prompt、模型路由或后处理，不自动启动 071。`inspect_casebook070.py` 和 `reference_spots070.py` 仅打印完整证据与输出供人工核对。
