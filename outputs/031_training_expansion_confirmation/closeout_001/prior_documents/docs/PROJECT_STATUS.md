# 项目现状总览

**030当前（2026-09-20）：** 固定Gate训练规模/组成分析已快速独立审计PASS，可冻结／结项。141个不同评价轮次，4356最终模型；11人训练时D对A/B合并平均同风险+5.11/+3.83R，但025子组仍多次反向、D更敏感。14人仅复现029锚点，不能据零波动证明组成稳健；现有数据不足以确定稳定最低人数或来源配比。0 API，不自动扩大训练材料、031或reserved40。 [主报告](../outputs/030_gate_training_stability/report.md) · [独立审计](../reviews/030_gate_training_stability.md)。

**029当前（2026-09-20）：** 离线36组实验已快速独立审计PASS，可冻结／结项。联合repeat+trace的Logistic在患者OOF相对A/B同风险混合包络多11/9R，保留该开发信号；反向迁移保留率71.1%，优势未稳定复现，XGBoost无可靠补救。不选winner、不继续特征/分类器搜索、不自动030或reserved40；0 API、0费用，独立029环境，未改历史结果。 [主报告](../outputs/029_semantic_information_gate/report.md) · [独立审计](../reviews/029_semantic_information_gate.md)。

**028当前（2026-09-19）：** 可追溯主张—证据核查已快速独立审计PASS，可冻结／结项。155个development候选，两臂各155次核心有效；trace仅保留44/110真S救回，相对SD完整队列净−40，相对repeat+9但区间跨0。未稳定超过完整global-λ参考，停止当前语义核查版本。费用估算3.798027/80元，不改λ/C48/历史结果，不自动029或reserved40。 [主报告](../outputs/028_traceable_claim_evidence_verification/report.md) · [独立审计](../reviews/028_traceable_claim_evidence_verification.md)。

**027当前（2026-09-19）：** 双Judge迁移瓶颈离线诊断已快速独立审计PASS，可冻结／结项。026排序仍有信息，但≥80% rescue区对完整global混合包络最多+2.368R，不能仅换阈值恢复门槛；22/52候选存在精确输入冲突。组成与概率尺度变化并存，现有证据不足以支持仅改工作点／融合器继续救Gate。0 API、0新增拟合、不改λ、不用reserved40，完成后停止。 [主报告](../outputs/027_dual_judge_transfer_diagnosis/report.md) · [独立审计](../reviews/027_dual_judge_transfer_diagnosis.md)。

**026当前（2026-09-19）：** 冻结SD跨患者组迁移已快速独立审计PASS，可冻结／结项。6人650条，D评分/B各650，仅52个候选调用Qwen；1352个核心有效，费用估算16.782714/80元。SD保留29/34救回、新增false-S18→12，但相对完整global随机混合包络仅+2.11R，留一患者4/6为正，未达事前门槛；停止当前版本，不调参、不自动reserved40。 [主报告](../outputs/026_frozen_sd_patient_transfer/report.md) · [独立审计](../reviews/026_frozen_sd_patient_transfer.md)。

**025当前（2026-09-19）：** 离线风险可分性分析完成，快速独立审计PASS，可冻结／结项。E未证明超出score/global λ的稳定增量，停止当前E路线；024D第二Judge信号有正向OOF增量，仅保留有限开发线索，历史D不可评估、Qwen未复现。固定λ=2、0新增API、未用reserved40，不自动后续。 [主报告](../outputs/025_lambda_flip_risk_separability/report.md) · [独立审计](../reviews/025_lambda_flip_risk_separability.md)。

**024当前（2026-09-19）：** 执行及评价完成，快速独立审计PASS，可冻结／结项。DeepSeek/Qwen均方向支持、均未达强迁移证据门槛；3515/3516核心有效，费用及未知预留57.534444/80元。固定λ=2、模型、prompt和API-BGE C48均未改，不使用reserved40。旧暂停及解析修订均保留。[主报告](../outputs/024_lambda2_transfer_validation/report.md) · [独立审计](../reviews/024_lambda2_transfer_validation.md)。023不自动启动024为此前边界，本次由用户另行授权；API路由和预算政策不变。


**023当前：** 023完成固定λ=2的零API响应/敏感性分析，快速独立审计PASS，可冻结／结项。019/020两轮在约1.946–2.079的标签平台内完全不变，±0.05无改判；较宽近性能区域有重叠，但峰位跨轮漂移，false-S随λ增大。固定λ=2未改，无新winner、不启动024或reserved40。[报告](../outputs/023_lambda_boundary_response_analysis/report.md) · [图表](../outputs/023_lambda_boundary_response_analysis/README.md) · [独立审计](../reviews/023_lambda_boundary_response_analysis.md)。

**022当前：** 022完成零API阶段A：16名development患者1529条R0＋879条R1折外评分，竞争感知与学习全局λ的2408条标签完全相同；相对U2正确数R0−28、R1−13，false-S虽减少但PA/MCC未达门槛。停止B/Qwen，保留λ=2；新增费用0/80元，快速独立审计PASS，可冻结／结项。[主报告](../outputs/022_competition_aware_support_calibration/report.md) · [独立审计](../reviews/022_competition_aware_support_calibration.md)。

022最新按模型分流：Embedding/reranker继续硅基流动Pro BGE并优先复用冻结缓存；主Judge直接阿里云DeepSeek V4 Flash，固定0731快照须在实际发送前核实，不等待硅基流动池耗尽。可选Qwen也走阿里云。022已在阶段A停止，本指示不自动启动新调用；历史019–021路由不回写。

更新：2026-09-20。001–030均有各自范围内的独立审计依据；019–030快速独立审计PASS，可冻结／结项。**审计通过不等于方法门槛或实现等价门槛通过。**

## 当前结论

| 任务 | 结论与边界 | 正式报告／独立审计 |
|---|---|---|
| 019 | 650条原低false-S门槛失败、无winner。λ2只是在原网格上事后识别的候选信号 | [报告](../outputs/019_support_boundary_screen/report.md) · [审计](../reviews/019_support_boundary_screen.md) |
| 020 | 固定λ2在新10名development患者879条上双轮确认。总体相对B/U0/O的PA和MCC两轮区间均正；false-S增加、NS损失、LLM MCC不稳。成绩属于API-BGE条件 | [报告](../outputs/020_lambda2_patient_validation/report.md) · [审计](../reviews/020_lambda2_patient_validation.md) |
| 021 | BGE本地化可运行，严格等价FAIL：仅换reranker reference一致594/879，全本地565/879。不能静默继承020成绩 | [报告](../outputs/021_bge_localization/report.md) · [审计](../reviews/021_bge_localization.md) |
| 022 | 16人1529条R0与879条R1折外筛查；竞争感知与全局λ同标签，较U2 PA/MCC不达门槛。停止收费阶段，保留λ2；0元 | [报告](../outputs/022_competition_aware_support_calibration/report.md) · [独立审计PASS](../reviews/022_competition_aware_support_calibration.md) |
| 023 | λ=2局部同标签平台及跨批次近性能范围，但峰位/风险并非不变；0API，不重新选λ | [报告](../outputs/023_lambda_boundary_response_analysis/report.md) · [独立审计PASS](../reviews/023_lambda_boundary_response_analysis.md) |
| 024 | DeepSeek/Qwen的U2−U0增益复现；U2−B的MCC区间跨0，均未达强迁移证据门槛。57.534444/80元；未用reserved40 | [报告](../outputs/024_lambda2_transfer_validation/report.md) · [独立审计PASS](../reviews/024_lambda2_transfer_validation.md) |
| 025 | E无稳定附加价值，停止；024D第二Judge有正向OOF线索，历史D不可评价、Qwen未复现，完整门槛无winner。0API | [报告](../outputs/025_lambda_flip_risk_separability/report.md) · [独立审计PASS](../reviews/025_lambda_flip_risk_separability.md) |
| 026 | 六人650条冻结SD迁移：R29/risk12，混合增量仅+2.11、LOO4/6为正；门槛未过，停止。16.782714/80元 | [报告](../outputs/026_frozen_sd_patient_transfer/report.md) · [独立审计PASS](../reviews/026_frozen_sd_patient_transfer.md) |
| 027 | 高rescue阈值曲线完整混合增量至多2.368R，22/52精确输入冲突；排序仍有信息，因果未定。不改Gate，0API/0拟合 | [报告](../outputs/027_dual_judge_transfer_diagnosis/report.md) · [独立审计PASS](../reviews/027_dual_judge_transfer_diagnosis.md) |
| 028 | trace保留44/110真S救回，相对SD净−40；未过门槛，停止当前版本，不自动029 | [报告](../outputs/028_traceable_claim_evidence_verification/report.md) · [独立审计PASS](../reviews/028_traceable_claim_evidence_verification.md) |
| 030 | k11合并平均+5.11/+3.83R，025仍反向；无法确定稳定最低人数，不冻结泛化Gate | [报告](../outputs/030_gate_training_stability/report.md) · [独立审计PASS](../reviews/030_gate_training_stability.md) |
| 029 | 联合信息OOF同风险+11/+9R，反向迁移保留71.1%；停止搜索，不选winner，不自动030 | [报告](../outputs/029_semantic_information_gate/report.md) · [独立审计PASS](../reviews/029_semantic_information_gate.md) |

020 all PA/MCC：R0 B72.92%/0.5268，U2 81.68%/0.5960；R1 B71.90%/0.5080，U2 80.55%/0.5711。false-S由17/16升至47/52。019未因020改变研究目标而回写成功；021未改变020原结果。

## 患者与研究边界

003固定20名探索、40名development、40名reserved test。**40名development均已用于开发／确认，已无未使用开发患者。** 021只复用020输入。reserved40人未用于019–021方法选择或评价；001/002已有全体汇总，不声称其任何层面从未接触。

λ2是development层面的固定候选验证信号，不是最终测试结论。原reason不会随离线U2改判更新，分数不是校准概率；最终论文方法和贡献仍须论证。进入reserved test前需另行冻结方法、评价及API/本地BGE实现选择，本次审计不启动测试。

## 已有证据如何衔接

- 001–003：数据与标签边界、统一评价、患者分组。
- 004–009：多轮实验与负结果；C48形成实用对照，未证明最优。
- 010–018：多层失败与双向代价并存。013多机制、015仲裁、016复核、017utility筛查停止；018支持优先研究Judge支持边界，但最大可优化净空间unknown。
- 019–021：从支持边界开发信号到固定候选确认，再到本地实现差异检查。旧失败不换名重跑；当前没有自动续跑任务。

## 环境、费用及复查

- [环境与安全重放](REPRODUCIBILITY.md)：原research-verifact负责计算；本地BGE另用environment.local-bge.yml声明关键依赖。旧执行脚本不直接用作日常复查。
- [API现行约定](API_POLICY.md)：022的BGE继续硅基流动缓存，主Judge直接阿里云0731；旧通用路由不覆盖022专项授权。跨阶段／账号／平台累计80元，历史预算保持。
- 019累计17.504163元，020累计44.28450852元，021新付费0元，均非账单；没有全池耗尽／已切平台的证据。
- 当前入口：[根任务表](../README.md#5-current-status)、[审计索引](../reviews/README.md)。各任务CURRENT_STATUS.md指向当前状态；冻结README、旧CURRENT、主报告、handoff和历史审计原文中的状态按形成时理解，不回写它们来模拟当时已经审计。
