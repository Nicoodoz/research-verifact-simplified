# 009：检索基线比较与证据损失定位

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/009_retrieval_baselines/report.md)。 独立结论查[审计末尾](../../reviews/009_retrieval_baselines.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

目标是在原 claim 和原医生标签不变的前提下，形成可继续使用的检索 baseline，并定位从原 EHR、索引、各路排名、候选融合、重排、打包到 Judge 的损失。沿用 002 统一评价；病例锚点不是完整医学 gold evidence。

先使用 008 的 144 条已开发命题及已存 embedding/回执，比较 A48（现有 BM25＋dense RRF）、B48（dense）、C48（两路交替去重保留）。索引、原 claim 重排、最终预算均固定。24 条固定哈希开发样本另比较 A/B80 容量、B48 有/无 rerank、B48 有/无每 note 上限；不是全量参数网格。规则及评价在新患者结果前冻结，再按原顺序第 19–24 名开发患者全部 650 条 valid claims 确认主要方案。保留 16 名后续开发患者及原 reserved test。

009 全任务 40 元上限，包含开发、确认、诊断和重试。预计约 28 元，不需用户再次确认。开发预算 6 元、确认 29 元、补充诊断 5 元，阶段路径固定，不能换账号/新子目录重置上限。没有付费预检；使用本地 `.env.siliconflow_pool`，不记录 key。

已完成：状态和唯一必读报告见 [输出入口](../../outputs/009_retrieval_baselines/README.md)。另有可选论文设置、结果表和相关工作草稿，明确实现修正与研究结论的区别。实际任务费用估算¥18.08218167，未核对账单；主确认三臂各650条预测完整。2026-09-15 修订定向独立复核 PASS，原重放阻塞关闭，可正式冻结／结项。

运行均在 Conda `research-verifact`。复用 008 的切段、BM25/dense 排序、选择器、原 Judge body、官方 API transport 和计费；新增独立预算阶段调度支持有限重试、未知费用预留、终止失败后继续未发送项。HTTP 200 不因标签、格式或内容重新生成。没有真实算过的 rerank 分数必须保持缺失，不填零。

## 当前可复用baseline

`baseline_config.json`登记本轮实际设置，暂定C48；`retrieval_baseline.py`提供纯本地 `retrieve(claim, passages, vectors, query_vector, method)` 与 `pack(candidate_ids, scores, passages, admission)`，A48/B48仍可选。输入为同患者真实EHR片段、与搜索文本及模型设置匹配的BGE-M3向量；返回候选后，用原claim和候选search_text取得真实BGE rerank分数再打包。没有分数时明确报错，不生成假分数。实际批量程序复用一个患者索引，接口便于后续小任务调用。

该接口导入不调用API、不读取key；最终Judge仍通过本轮冻结的普通structured模板构造原claim＋reference。后续新任务须建立自己的输入和预算记录；不要通过重建009阶段目录重新收费运行已有答案。

## 离线复核

从项目根目录、Conda环境中运行，输出目录必须不存在：

```powershell
python -B tasks/009_retrieval_baselines/verify009.py --output outputs/009_retrieval_baselines/verification_local
```

此入口禁用网络，重建原文切段、向量、排名、候选、打包、回执评分及案例引用，保存143项测试日志；不新增推理。只重评分可运行 `score009.py <development_001或confirmation_001目录> <dev_judge或confirm_judge> --output <新目录>`；事后干预使用 `score_interventions.py --output <新目录>`。完整body缓存与回执均严格绑定。可变根README、AGENTS及审计文档不属于实验重放锁定材料。

正式实际代码与文件指纹见[交审入口](../../outputs/009_retrieval_baselines/audit_handoff.md)。主比较、诊断和历史临时/修订记录不得混写；审计期间停止修改同批成果。

## 009 审计后的重放修订

审计指出的工作区文件白名单阻塞已修订并通过2026-09-15定向独立复核，问题关闭。Git变更仅作为诊断信息；冻结实验材料继续严格校验，旧自查程序版本单列来源记录。当前146项断网测试通过，109个内容文件重放不变，无API调用。修订说明与实际版本见[revision_001](../../outputs/009_retrieval_baselines/revision_001/README.md)。此前143项测试、原交审清单和独立审计意见保持历史记录。

当前独立结论见[审计末尾追加](../../reviews/009_retrieval_baselines.md)；修订说明保留交审时状态，科研限制不因任务结项消失。
