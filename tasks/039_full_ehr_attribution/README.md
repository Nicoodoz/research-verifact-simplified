# 039 Full-EHR Attribution Audit

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/039_full_ehr_attribution/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

目标：解释038/036中U2 Supported翻转究竟来自C48已有证据、C48漏检、部分支持还是未找到清楚支持。

执行：
- 462条claim-only query expansion；
- 遍历036目标住院eligible EHR完整dense/BM25排序；
- 原C48 + 32个最高排名C48外passage做GT盲Qwen证据审计；
- A/B/C/D/U归因只作post-hoc mechanism analysis。

结果入口：outputs/039_full_ehr_attribution/report.md
核验：outputs/039_full_ehr_attribution/verification_001.json
独立审计待进行；不自动修改036方法。
