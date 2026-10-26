# 088：保留判定依据的固定示例压缩

状态：**构造阶段完成，按输入等价停止**。2次真实Qwen构造回答均要求长示例保留全文，P4=Q4=F4；没有主评价，不是待续跑队列。

[事前协议](protocol.md) · [中文报告](../../outputs/088_evidence_preserving_demonstration_compression/report.md) · [审计交接](../../outputs/088_evidence_preserving_demonstration_compression/audit_handoff.md)

`common088.py`负责可追踪完整原文单元；`construct088.py`实现P/Q构造、标签盲源核对和最多一次源ID追加；`api088.py`覆盖全任务费用/有限恢复。短槽及任何无法可靠处理的槽位保留原文，不按四个ID写特判。未实际运行的核对/Q比较能力不冒充实测验证。

零API合成测试：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/088_evidence_preserving_demonstration_compression/test088.py`。

只读复核：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/088_evidence_preserving_demonstration_compression/verify088.py`。

不重新运行已结项收费构造，不重试成功回答，不擅自恢复R1/AWS或新任务。默认B不变。
