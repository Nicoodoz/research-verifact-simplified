# 068：final pack 效用诊断——中文报告

## 决策摘要

**当前不训练 final-pack utility selector，也不继续修改 packer/prompt。** 066 的 GT-aware oracle 说明 C48→final pack 存在可观察空间，但不能证明这种空间可由 GT 盲规则稳定识别。068 复核发现，067 仓库内部有两套相互冲突的“正式”口径：后来的 067 报告采用了实现无效的 v1 请求；较早的 v2 冻结和执行备注则明确将 v1 排除。**论文和后续方法判断应暂缓引用 067 的 v1 主指标，先做独立来源审计。** 本报告把两套工件严格分开。

实现修正的 v2 分支在 236 条 development claim 上有小幅 raw Judge 收益，但 Frozen PriorG 后原先的 2 条救回在同输入重复中都没有重现。按 068 事前决策规则，**没有足够稳定且可由 GT 盲信号识别的系统级效用监督**。这不证明前处理没有价值；它说明当前材料尚不足以支持学习/部署一个选择器。

## 协议、数据与口径

- 事前[协议](../../tasks/068_final_pack_utility_diagnosis/protocol.md)固定了 052 T-S thinking-high scoring Judge、053 Frozen PriorG、development 队列、统一三分类评价和 10 元总费用上限。发现历史实现及口径问题后、相应新增调用前保存了四份[预检修订](../../tasks/068_final_pack_utility_diagnosis/protocol_amendment_004.md)；未改成功门槛。
- 自然主队列为 052 T-S 有效的 **236 条／24 名患者**。原包、v1、v2 分别用完整同 ID 样本，调用 `verifact_research.evaluation.evaluate` 与 `paired_compare`，valid-only、micro PA/AC1/MCC、1,000 次患者 cluster bootstrap。重复子集只作稳定性诊断，不当作自然队列性能。
- 原 067 的 052、v1 和 v2 回执保持原样。068 新请求只送 proposition 与 EHR reference，不含 GT、历史预测或干预结果；不使用 reserved，不重新调 PriorG，不扩大检索。

## 先核清 067 的真实干预

| 分支 | 冻结与执行工件 | 实际 pack 行为 | 067 文档口径 |
|---|---|---|---|
| v1 | `cases_blind`、`stage1_jobs`、`stage2_jobs` | 236 条 `baseline_pids` 全为空；227 个 audit 的 `current_pack_ids` 全为空；226 个改包把原平均 11.89 段变成 1–2 段 | 较早 `freeze_v2`/`execution_note_002` 标为实现无效；较晚 `CURRENT_STATUS`/`report_final` 却把它当正式结果 |
| v2 | `cases_blind_v2`、`stage1v2_jobs`、`stage2v2_jobs` | 225 条映射到原包的病例均有非空 passage ID；27 条改包显式新增 33 段、删除 38 段，原包/新包均约 11–12 段 | 较早冻结和执行备注称其为正式修正；较晚账务修订把它列为 post-formal 排除 |

v1 的 `dropped_pids=[]` 只说明代码没有执行显式 drop：它从空的 baseline ID 列表开始构造新包，**实际并未保留原包**。其 424 个所谓 addition 中，有 310 个 passage 全文已出现在原 reference，114 个才是原包未见的文本。v1 真正混合了大幅删减/聚焦、部分新增以及格式变化，不能用来否定“保留原包后谨慎补证据”。067 原有 artifact replay 自检核对了请求与实现的一致性，却没有检查“原包应被保留”的语义不变量。

v2 修复了原包映射，但它的 27 次改包也不是单一“只新增”操作：26 次同时有 addition 和 drop，只有 1 次仅新增。两个原先救回病例分别为“增 1、删 1”和“增 1、删 2”。因此即使个别标签变好，现有 v2 回执也无法把作用分配给**新信息、删除干扰、证据组合或呈现**中的某一个。v2 已有完整原包映射，且最终 reference 不含 v1 的字面量换行分隔符；仍缺少只增、只删、同信息换序的同期对照。

形成时间与口径冲突均保留：[v2 冻结文件](../067_conservative_evidence_packing/freeze_v2.json)在 2026-09-23 04:50 UTC 写明 v1 无效；[执行备注](../067_conservative_evidence_packing/execution_note_002.md)在 05:14 UTC 写明 v2 为正式；较晚[当前状态](../067_conservative_evidence_packing/CURRENT_STATUS.md)和[账务修订](../../tasks/067_conservative_evidence_packing/protocol_amendment_001.md)又反向指定。068 不替独立审计追认任一历史声明。两套预测不能择优或合并。

## 分支结果：raw 与 Frozen PriorG 分开

| 236 条同 ID | Raw T-S correct / MCC / false-S | Frozen PriorG 后 correct / MCC / false-S | 配对变化 |
|---|---:|---:|---|
| 原 052 baseline | 177 / 0.5058 / 3 | 198 / 0.5946 / 6 | 共同基准 |
| v1 错误实现（仅诊断） | 177 / 0.5159 / 3 | 199 / 0.5819 / 10 | final 14 rescue、13 harm；不能作为保守补证据方法成绩 |
| v2 修正分支 | 181 / 0.5238 / 3 | 200 / 0.6085 / 6 | raw 4 rescue、0 harm；final 2 rescue、0 harm |

统一评价的患者聚类 95% 区间：v2 raw 相对原包 ΔMCC **+0.0180 [ +0.0035, +0.0364 ]**；v2 PriorG 后 ΔMCC **+0.0139 [ −0.0003, +0.0351 ]**。v2 的原始结果仍未达到 067 事前晋级门槛：净正确 +2 < +3，ΔMCC +0.0139 < +0.015，救回只覆盖 2 名患者 < 3。不能把 raw 正向区间当成最终系统晋级。

## 同输入波动与呈现

068 对 v2 **全部 27 条真正改包病例**重复 final pack 判断；原包同输入重复 27 条，其中 5 条复用本轮已经得到的完全相同请求体回答。v2 原先的 **2/2 条 final rescue 均未重现**；重复轮次 27 条均无 PriorG 后的 rescue 或 harm。原包自身 final 标签翻转 1/27，v2 pack 自身翻转 3/27。Raw 层的 4 条原 rescue 在重复中仍有 4 条 rescue，其中 **3 条是同一病例、覆盖 3 名患者**；这表明有有限的 raw 响应信号，但它没有形成稳定的 Frozen PriorG 后净收益。上游改变后必须报告这一兼容性，不能同步调后处理来挽救本轮结论。

v1 错误实现的诊断性同输入重复覆盖原 14 rescue、13 harm，加 12 个按 ID 哈希取的无净变化对照，共 39 条。原 14/13 中只有 **9/6** 在重复配对中同向出现；原包 final 标签自翻转 5/39，v1 短包 13/39。另对 37 条将字面量 `\n` 改成真实换行，final 标签与原短包不同 12/37；短包同输入重复自身亦翻转 13/39。故这个格式对照不足以把呈现效应从随机波动中可靠分离。v1 的任何“稳定”效用及 GT 盲信号都不得算作 v2 的可学习证据。

一次重复只能提供有限的稳定性信息。v2 改包病例中 GT 为 S/NS/NA 的数量是 **24/2/1**，无法据此评价 NA exact-addressability 的普遍表现。

## GT 盲信号与学习决策

v2 原结果仅有 2 个 final rescue、0 harm；重复后 **0 个稳定 final rescue**，无法估计有益/有害改包的可泛化区分能力。原先两个救回所加 passage 的角色分别是 temporal 和 direct_contradiction，但每类只有 1 条，不能据此拟合规则。

作为错误实现的警示，v1 的 27 个原 final flip 中，带 `direct_contradiction` role 的 6 条全为 rescue、0 harm；重复仍为 4 rescue、0 harm。该角色在发送前可见，但 v1 audit 完全没有原包 ID，所测是另一种意外操作；样本又已按结果诊断，不能把这个关联移植为 v2 的 no-change gate。历史 017 的有限单段替换在 19 条稳定基准错误中没有稳定救回；066 的 11 条 evidence-oracle 修复使用了 GT，亦不是 GT 盲可学习性的证明。

068 事前继续学习规则要求 ≥3 个跨 ≥3 患者的重复救回、重复救回多于伤害、并有稳定方向的 GT 盲区分信号。**v2 在第一项即失败；第三项因事件数不足不可验证。** 决策是停止从当前 067 材料训练 selector，也不事后改用 v1 的关联宣布成功。

## 费用、核验与下一步

- 阿里云北京 `deepseek-v4-flash-0731` 忙时公开单价为输入 ¥3／百万 token、输出 ¥9／百万 token，按最高忙时价保守预留；依据为[阿里云百炼模型价格表](https://help.aliyun.com/zh/model-studio/model-pricing)。实际 usage 估算并非账单。
- 068 新增 164 次请求，**164/164 HTTP 200**；78 次 v1 同输入重复约 ¥1.835706，37 次 v1 格式对照约 ¥0.619701，49 次 v2 同输入重复约 ¥1.329873；合计 **¥3.785280／10 元**，未知预留 0。5 条 v2 原包重复直接复用同 body 回执，不重复计费。没有重试、reserved 使用或后续收费阶段。
- [冻结清单](freeze_v2_068.json)、[费用与执行记录](execution_v2.json)、[逐例 v2 结果](diagnostic_v2_cases.jsonl)、[统一评价](unified_evaluation_v2.json)及[自检](verification.json)均已保存。执行者自检 **1346 PASS、0 FAIL**；独立审计未执行。原始数据和 066/067 冻结工件未改。

**下一步最有信息价值的动作**是先独立审计 067 的来源与口径冲突，并在论文中更正 v1 的机制解释。若之后继续研究 final pack，应在新的患者隔离材料上，事前固定只增、只删、二者组合、同信息呈现四个对照和同输入重复，重点检验“同主体、同事件、同时间、同关系”的 decision-critical gap。当前不自动启动该实验或 069。
