# 067：Conservative Requirement-Preserving Evidence Packing

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/067_conservative_evidence_packing/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

067旧版本来源与口径争议已有[069追加更正](../../outputs/069_final_pack_controlled_repair/067_correction.md)，不能把旧v1数值当现行方法证据。

## 原任务阶段说明（历史）

067针对066定位的C48→final pack瓶颈，测试“保留原pack，只从C48最多补2段、禁止自由裁剪”的GT-blind conservative packing。

052自然236条：
- Baseline T-S+PriorG：198/236，PA 83.90%，MCC 0.5946，false-S 6。
- 067：199/236，PA 84.32%，MCC 0.5819，false-S 10。
- rescue/harm/net = 14/13/+1。
- advance=false。

Raw T-S层correct不变177/236，MCC 0.5058→0.5159，false-S保持3；NS recall 50.0→72.2%，但NA recall 77.4→64.5%。

主要诊断：
1. 226/227可审计claim都被修改，触发过宽；
2. 424个addition、0 drop，平均+1278字符，导致普遍context augmentation；
3. 新证据有助NS-vs-NA，但把大量NA推成NS；
4. Frozen PriorG在新score geometry上兼容性下降，raw false-S不变但final false-S升到10；
5. 下一版需高精度NO-CHANGE/gap gate与NA exact-addressability，而不是继续全量补证据。

正式453/453 HTTP200，费用约¥11.84。另252个post-formal superseded v2回执不计正式结果。verification_002 2984项PASS、0 FAIL；独立审计未执行。
