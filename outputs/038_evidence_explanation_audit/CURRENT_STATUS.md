# 038 当前状态

状态：执行与执行者自检完成；独立审计待进行。

核心结果：
- U2最终Supported 2647条中，346条继承自原scoring non-S verdict/reason，占13.07%。
- 346条解释冲突由Qwen审计，346/346判为contradictory。
- 219条GT=Supported的U2救回中，Qwen证据审计有效214条：68条判Supported，51条满足strict trace-supported；DeepSeek有效206条，仅2条判Supported/strict trace-supported。
- 两模型都有效的201条R中，133条都给non-S；自动证据审计不是医生gold，不能把这些比例当真实证据充分率。
- 1270个HTTP200，实际usage估算约12.052014元；未重跑任何HTTP200。
- 038不改036标签结果、不重新选择λ/Gate/校准器；只收紧论文主张边界。

入口：[主报告](report.md) · [执行者核验](verification_001.json) · [交审](audit_handoff.md)
