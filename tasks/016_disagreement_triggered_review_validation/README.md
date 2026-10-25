# 016：分歧触发独立复核的前瞻验证

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/016_disagreement_triggered_review_validation/report.md)。 独立结论查[审计末尾](../../reviews/016_disagreement_triggered_review_validation.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

用户交办将015的evidence_only正向观察作为新假设，用未参与该方法开发的患者检验，并区分分歧门控、普通重复、独立review的作用。不是015候选理由仲裁的v2，也不改变检索/packing。

当前第一阶段因服务失败导致费用重估超40元而停止，实验未完成、未作GT性能评价。003开发序第25–30名六患者601条；只收V4 122/Qwen124份有效基础回答，累计估算及预留¥5.81291603，无分歧复核。剩余开发与reserved test不参与。唯一必读[主报告](../../outputs/016_disagreement_triggered_review_validation/report.md)。

冻结[修订事前协议](../../outputs/016_disagreement_triggered_review_validation/protocol_002.md)后构造相同C48，全量同期V4/Qwen，仅分歧各跑一次普通V4重复与015原版独立review。明确门槛未通过就停止；通过也仅建议第二阶段，不自动执行。

旧protocol_001、preparation_001、precharge_history_001是未收费旧预案。正式输入为stage1/preparation_002。prepare016 → build016 candidates → build016 judge → build016 review依序产生任务；每次run016前必须由budget016生成该jobs文件的费用估算。全任务只有一份authority_001和live/ledger.json。run016不接受confirmation或其他chat目录。

analyze016/render016/verify016为完整实验的预先准备工具，本轮未调用。停止状态使用verify_interruption016离线重建C48、body、部分标签、费用，并检查001–015文件和Windows检出。自查不等于独立审计。保留task_api.lock防止误续跑；原live台账不回写，在途请求按未知保留费用，见interruption_001。当前没有自动恢复或后续实验授权。
