# 文档说明（2026-10-26）

根目录只保留现行状态与规则：[项目现状](PROJECT_STATUS.md)、[研究原则](RESEARCH_EXECUTION.md)、[API政策](API_POLICY.md)、[运行环境](RUN_ENVIRONMENT.md)、[复现说明](REPRODUCIBILITY.md)、[任务索引](TASK_INDEX.md)。执行模型还须遵守根[AGENTS](../AGENTS.md)。

| 子目录 | 内容 |
|---|---|
| [reports](reports/) | 导师汇报、PDF及F4 raw复核数据 |
| [papers](papers/) | 论文稿、修改指南、写作资料、ZIP及配套assets图片 |
| [reading](reading/) | 原论文与源码审读、文献筛查、论文／数据笔记、单病例导读 |
| [prompts](prompts/) | 历史执行提示词、任务计划及部署准备；不是待自动执行的任务 |
| [sharing](sharing/) | GitHub精简副本与Gemini阅读说明 |
| [aliyun](aliyun/)／[siliconflow_pool](siliconflow_pool/) | 服务接入及客户端说明，凭据不放文档目录 |
| [sources](sources/) | 引用论文、模型资料与上游源码快照 |
| [history](history/)／[maintenance](maintenance/) | 旧快照及维护记录 |

当前研究完成至097；[095结项完整稿](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)是历史底稿，不证明当前同模型raw目标已经达成。后续修改看[papers/02_revision_handoff_zh.md](papers/02_revision_handoff_zh.md)。旧v1/036/094稿和历史提示词按形成时解读，不覆盖最新授权。

067须结合[069更正](../outputs/069_final_pack_controlled_repair/067_correction.md)，086须结合[087更正](../outputs/087_f4_evidence_intervention/086_correction.md)，083须结合[084离线结项](../outputs/084_f4_coverage_validation/083_oof_diagnosis.md)。085正式Valdemardi实验与旧AWS准备分支不同。独立审计范围见[审计索引](../reviews/README.md)。

本次实际移动文档，不新增分组导航页、不移动tasks/outputs。旧协议、manifest及历史脚本保留原路径记录；严格重放使用对应历史checkout，不改写旧哈希。新旧位置见[迁移清单](maintenance/2026-10-26_docs_moves.json)。
