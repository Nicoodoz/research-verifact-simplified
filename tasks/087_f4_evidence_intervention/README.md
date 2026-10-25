# 087 F4证据信息干预与紧凑示范验证

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/087_f4_evidence_intervention/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

用户交办的四臂受控实验：B／原F4／删除示例reference的CL4／固定置换reference的X4。

- [收费前协议](protocol.md)与[必要文献/价格核对](related_work.md)。
- [冻结队列与输入](../../outputs/087_f4_evidence_intervention/freeze.json)，110条／22患者，440请求，累计20元原价硬上限。
- [主报告](../../outputs/087_f4_evidence_intervention/report.md)，[086追加更正](../../outputs/087_f4_evidence_intervention/086_correction.md)。

只读状态：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/087_f4_evidence_intervention/run087.py status`。

零API合成测试：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/087_f4_evidence_intervention/test087.py`。

零API自检：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/087_f4_evidence_intervention/verify087.py --output <全新JSON路径>`。拒绝覆盖已有文件；自检不是独立审计。

`prepare087.py`、`analyze087.py`和`correct086.py`生成任务固定工件，拒绝覆盖，不能作为无写入的日常查看命令。`run087.py run`是唯一收费入口，结项后不得无新授权增加请求；成功回执不会重新发送。默认系统和历史文件不变，085A/R1/AWS继续暂停。
