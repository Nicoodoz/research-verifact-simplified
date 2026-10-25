# 066：Oracle Headroom Decomposition

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/066_oracle_headroom/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

066冻结现有后处理 T-S + Frozen PriorG，把053剩余39个错误拆成前处理与LLM推理headroom。

主要结果：
- baseline MCC 0.5607；
- same-reference observed reasoning oracle MCC 0.7101；
- GT-aware raw-EHR evidence oracle + 当前T-S+PriorG MCC 0.6680；
- 二者并集 MCC 0.7968。

错误四格：reasoning-only 11、evidence-only 8、both 3、neither 17。

Evidence Oracle修对11条中，9条关键passage本来已在C48但原final pack没完整选入，1条原final reference已有全部oracle证据但重组后才修复，仅1条需要C48外证据/混合检索。当前前处理首要瓶颈因此是C48→final reference，而非扩大retrieval。

该任务是GT-leaking oracle/headroom诊断，不是可部署方法或最终论文成绩。最终Judge从不接收GT，只看真实原始EHR reference。

113/113 HTTP200，费用约¥2.30，reserved未使用，143项executor verification PASS，独立审计未执行。
