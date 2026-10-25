# 008：LLM 检索规划

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/008_retrieval_planning/README.md)。 独立结论查[审计末尾](../../reviews/008_retrieval_planning.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

已通过2026-09-14精简独立审计，无阻塞修正；依据见[审计记录](../../reviews/008_retrieval_planning.md)。 原主报告、交审清单、自查记录以及报告源稿中的“等待审计”保留形成时状态；以本入口和审计最新结论判断任务状态。后续研究优先级以[009入口](../../outputs/009_retrieval_baselines/README.md)为准，旧建议不是新的待执行授权。 tasks目录中的report.md/report_template.md及research_notes是本任务报告源稿或定向阅读底稿，不是滚动更新的项目状态页。

研究问题：固定原 atomic claim，让 LLM 将来源线索转换为寻找支持或反证的短查询，能否比直接 claim 和直接来源扩展找到更合适的患者 EHR，并提高原医生标签一致性？本任务是开发组可行性验证，不是保留测试成绩，也不以正结果为完成条件。

本次沿 003 冻结哈希顺序使用此前未逐例分析的第 13–18 名开发患者：84454、67117、71743、72844、93788、26858。每患者每作者选 12 条有效 claim，共 144 条；先固定哈希取最多 3 条 NS、3 条 NA，再用 S 和剩余命题补足。LLM 为 S/NS/NA=67/4/1，human 为 41/13/18。这是刻意增加少数类覆盖的小样本，不代表总体患病率或 benchmark 分布。

执行前协议见 [冻结协议](../../outputs/008_retrieval_planning/execution_protocol_001.md)，输入清单见 [preparation_001](../../outputs/008_retrieval_planning/preparation_001/summary.json)。最终只需阅读结果入口所指向的一份中文主报告：[008 结果入口](../../outputs/008_retrieval_planning/README.md)。

当前用户长期授权：预计一项任务新增 API 总费用不超过 **40 元**可直接执行。本次预计约 8.85 元，五阶段预算合计硬上限 40 元。没有收费预检，使用 `.env.siliconflow_pool` 的既有账号池；凭据不进入成果。只调用硅基流动官方服务，回执原样保存，已有成功回答不重生成。费用为公开价格与 usage 估计，不是账单。

离线入口：`prepare_experiment.py` 准备；`check_preparation.py` 核对；`build_stages.py` 处理回执和构建后续阶段；`score_results.py` 调用 002 统一评价。收费入口 `execute_phase.py` 必须验证预算授权、冻结输入与执行代码哈希后运行。所有 Python 使用 Conda `research-verifact`。

不得修改原始数据、历史 run、独立审计意见。分析标签和证据锚点均为执行者阅读诊断，不是新增医生 GT。模型生成解释只作为可观察输出，不能证明内部因果机制。
