# 068：final pack 效用诊断（执行前冻结）

## 研究问题和范围

诊断 C48 到 final evidence pack 的改动效用，不开发新 packer、prompt、selector 或后处理。固定 052 的 T-S thinking-high scoring Judge 和 053 Frozen PriorG。只用 development；reserved 不参与开发。所有新增 Judge 输入只有原 proposition 与真实 EHR reference，无 GT、历史预测或干预结果。新增付费请求跨预检、重复、失败和未知预留共用人民币 10 元硬上限；不拆阶段重置。

## 数据与分析分层

1. 067 的自然 236 条为主队列，完整报告 raw Judge 与 PriorG 后的原包、增补包、配对变化及患者聚类区间。正式预测严格只用 067 formal stage1/stage2；post-formal v2 回执不参与正式评价。
2. 067 的 14 个最终 rescue 与 13 个最终 harm 全部进入稳定性诊断，不只挑成功病例。另从 changed 且最终标签正确性未变化的病例中，按固定 SHA-256(ID) 顺序取最多 6 个原本正确、6 个原本错误的对照；对照不用于学习或选择方法。
3. 066 的 GT-aware oracle 仅作机制线索和可观察上限，绝不作为可部署学习监督。065 的 focus-only、017 的同输入重复及小替换作为不同队列的外部历史参照，不合并指标或假装同一受控实验。

## 实验对照

对第 2 条选中的病例，各新增一次**原包同输入重复**和一次**067 增补包同输入重复**，请求体直接复用原冻结 T-S builder；原回执不改写。额外构造“只重新呈现原 baseline passages”的 reference：使用 067 同一 corpus、同一 chronological formatter、同一 baseline passage IDs，不加入 C48 passage。若其请求体与原包逐字相同，直接复用，不收费；若不同，仅对 14 rescue + 13 harm 构造此呈现对照。准备阶段按 ID 的 SHA-256 顺序给呈现对照排序，在总保守预留不超过 9.5 元时纳入尽可能多的病例；剩余至少 0.5 元为失败/未知保护。此选择只依赖既有 067 结果和请求长度，不依赖 068 新回答。

原包→重新呈现原包只检验呈现/顺序变化；重新呈现原包→067 增补包同时包含新增文本与它同原有证据的组合，不能仅凭标签变化把新增信息和组合效应拆成独立因果量。067 从未删除 baseline passage，因此它本身不能估计“删除干扰”的收益；065 的裁剪案例只作有限历史证据。

HTTP 200 即保存并解析，不能按答案内容重跑或择优。非 200 或未知结果占用费用预留并停止新增发送；不把缺失当有效预测。所有请求先冻结 ID、body hash、输入来源和成本上界，再发送。

## 预设诊断与决策

- 稳定性：原 067 配对效果须在两个条件的同输入重复中同向出现才称“重复救回/伤害”；同时报告原包自身、增补包自身的标签翻转率，以及 raw 和 PriorG 的分歧。一次重复只能给有限稳定性证据。
- 机制：报告 067 的 0 drop、baseline block 完整性、原始/最终 block 顺序、baseline-only 呈现对照；按新增段与原包文本的词组重叠量报告重复性。所有近重复和“decision-critical”解释都只是自动/研究者诊断，不是医生 passage gold。
- GT 盲可用信号：仅考察干预前可见的新增段数量、长度变化、Qwen role/requirements/unresolved、baseline score margin、作者，以及预定义的 claim↔新增 passage 词项覆盖和新增段相对原包的词项新颖度。不能用 GT、067 救回/伤害、Judge 新输出作特征。逐项报告 rescue/harm 分布和患者聚类不确定性；小样本不训练复杂 selector、不挑事后最优阈值。
- 有进一步学习依据须同时看到：至少 3 个跨至少 3 名患者的重复救回，重复救回多于重复伤害，以及至少一个事前列出的 GT 盲信号在救回/伤害间有稳健方向（患者 bootstrap 的 AUC 区间下界 >0.5）。否则结论为“当前材料不足以支持训练 selector”，并说明是效用本身不足、波动过大，还是信号不可分；不把未证实写成不存在。

统一调用 `verifact_research.evaluation.evaluate` / `paired_compare`，主分析 valid-only、完整同 ID、三分类 micro、1,000 次患者 cluster bootstrap。诊断性抽样单列，不能把它当自然队列性能。

## 交付

保存冻结清单、费用台账、原始回执、逐例结果、统一评价、重复与机制诊断、自检及中文报告。明确三个研究问题的回答与下一步决策。独立审计与执行者自检分开。本轮不 commit/push；068 结束后不自动启动 069。
