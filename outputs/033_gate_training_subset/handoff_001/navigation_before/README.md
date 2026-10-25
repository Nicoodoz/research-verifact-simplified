# Research-VeriFact

**032当前（2026-09-20）：** 证据关系增强三分类纠错已快速独立审计**PASS，可冻结／结项**。28名/2527条训练，12名/1148条已暴露确认；NLI配对54236组、135套保存模型。双粒度注意力主方案954/1148，PA 83.10%、MCC 0.4960、错误Supported 77；λ=2参照947/1148，PA 82.49%、MCC 0.5210、错误Supported 57。未实现PA/MCC共同提高，不因辅助结果改选主方案。0新收费API，未使用reserved40，未修改主环境或029环境，不自动033；本轮用户授权通过后提交推送。[主报告](outputs/032_evidence_relation_correction/report.md) · [当前状态](outputs/032_evidence_relation_correction/CURRENT_STATUS.md) · [独立审计](reviews/032_evidence_relation_correction.md)。

**031当前（2026-09-20）：** 固定信息组合的训练扩充/患者隔离确认已快速独立审计PASS，可冻结／结项。原16人扩至28人，另12人1148条完整确认；扩充后A/B正确数不变，C/D各+1。主要同风险混合差C−A为−3.50R、D−B为−5.14R，未确认新增核查信息的实质增量，停止当前版本；A仅保留简单参照。费用及未知预留37.70924338/80元，不使用reserved40、不自动032；本轮用户授权审计通过后提交推送。031由用户另行授权，不回写030边界；长期API政策和主环境未改。 [主报告](outputs/031_training_expansion_confirmation/report.md) · [独立审计](reviews/031_training_expansion_confirmation.md) · [离线复查](outputs/031_training_expansion_confirmation/audit_handoff.md)。

**030当前（2026-09-20）：** 固定Gate训练规模/组成分析已快速独立审计PASS，可冻结／结项。141个不同评价轮次，4356最终模型；11人训练时D对A/B合并平均同风险+5.11/+3.83R，但025子组仍多次反向、D更敏感。14人仅复现029锚点，不能据零波动证明组成稳健；现有数据不足以确定稳定最低人数或来源配比。0 API，不自动扩大训练材料、031或reserved40。 [主报告](outputs/030_gate_training_stability/report.md) · [独立审计](reviews/030_gate_training_stability.md)。

**029当前（2026-09-20）：** 离线36组实验已快速独立审计PASS，可冻结／结项。联合repeat+trace的Logistic在患者OOF相对A/B同风险混合包络多11/9R，保留该开发信号；反向迁移保留率71.1%，优势未稳定复现，XGBoost无可靠补救。不选winner、不继续特征/分类器搜索、不自动030或reserved40；0 API、0费用，独立029环境，未改历史结果。 [主报告](outputs/029_semantic_information_gate/report.md) · [独立审计](reviews/029_semantic_information_gate.md)。

**028当前（2026-09-19）：** 可追溯主张—证据核查已快速独立审计PASS，可冻结／结项。155个development候选，两臂各155次核心有效；trace仅保留44/110真S救回，相对SD完整队列净−40，相对repeat+9但区间跨0。未稳定超过完整global-λ参考，停止当前语义核查版本。费用估算3.798027/80元，不改λ/C48/历史结果，不自动029或reserved40。 [主报告](outputs/028_traceable_claim_evidence_verification/report.md) · [独立审计](reviews/028_traceable_claim_evidence_verification.md)。

**027当前（2026-09-19）：** 双Judge迁移瓶颈离线诊断已快速独立审计PASS，可冻结／结项。026排序仍有信息，但≥80% rescue区对完整global混合包络最多+2.368R，不能仅换阈值恢复门槛；22/52候选存在精确输入冲突。组成与概率尺度变化并存，现有证据不足以支持仅改工作点／融合器继续救Gate。0 API、0新增拟合、不改λ、不用reserved40，完成后停止。 [主报告](outputs/027_dual_judge_transfer_diagnosis/report.md) · [独立审计](reviews/027_dual_judge_transfer_diagnosis.md)。

**026当前（2026-09-19）：** 冻结SD跨患者组迁移已快速独立审计PASS，可冻结／结项。6人650条，D评分/B各650，仅52个候选调用Qwen；1352个核心有效，费用估算16.782714/80元。SD保留29/34救回、新增false-S18→12，但相对完整global随机混合包络仅+2.11R，留一患者4/6为正，未达事前门槛；停止当前版本，不调参、不自动reserved40。 [主报告](outputs/026_frozen_sd_patient_transfer/report.md) · [独立审计](reviews/026_frozen_sd_patient_transfer.md)。

**025当前（2026-09-19）：** 离线风险可分性分析完成，快速独立审计PASS，可冻结／结项。E未证明超出score/global λ的稳定增量，停止当前E路线；024D第二Judge信号有正向OOF增量，仅保留有限开发线索，历史D不可评估、Qwen未复现。固定λ=2、0新增API、未用reserved40，不自动后续。 [主报告](outputs/025_lambda_flip_risk_separability/report.md) · [独立审计](reviews/025_lambda_flip_risk_separability.md)。

**024当前（2026-09-19）：** 执行及评价完成，快速独立审计PASS，可冻结／结项。DeepSeek/Qwen均方向支持、均未达强迁移证据门槛；3515/3516核心有效，费用及未知预留57.534444/80元。固定λ=2、模型、prompt和API-BGE C48均未改，不使用reserved40。旧暂停及解析修订均保留。[主报告](outputs/024_lambda2_transfer_validation/report.md) · [独立审计](reviews/024_lambda2_transfer_validation.md)。023不自动启动024为此前边界，本次由用户另行授权；API路由和预算政策不变。


**当前023：** 023完成固定λ=2的零API响应/敏感性分析，快速独立审计PASS，可冻结／结项。019/020两轮在约1.946–2.079的标签平台内完全不变，±0.05无改判；较宽近性能区域有重叠，但峰位跨轮漂移，false-S随λ增大。固定λ=2未改，无新winner、不启动024或reserved40。[中文主报告](outputs/023_lambda_boundary_response_analysis/report.md) · [Figure 1](outputs/023_lambda_boundary_response_analysis/figures_001/figure1_performance.pdf) · [独立审计](reviews/023_lambda_boundary_response_analysis.md)。

**当前022：** 022完成零API阶段A：16名development患者1529条R0＋879条R1折外评分，竞争感知与学习全局λ的2408条标签完全相同；相对U2正确数R0−28、R1−13，false-S虽减少但PA/MCC未达门槛。停止B/Qwen，保留λ=2；新增费用0/80元，快速独立审计PASS，可冻结／结项。[中文主报告](outputs/022_competition_aware_support_calibration/report.md) · [独立审计](reviews/022_competition_aware_support_calibration.md)。

**此前已审状态：019–021快速独立审计PASS，可冻结／结项。** 019原低false-S保护门槛失败；020固定λ2在最后10名development患者879条上取得双轮总体PA/MCC正向结果，但有false-S增加、NS损失及LLM不稳定；021本地BGE可运行但严格等价FAIL（全本地reference一致565/879），不能继承020成绩。

40名development均已使用；40名reserved test未用于019–022方法选择或评价。本次不启动最终测试。U2离线改判未同步改写原reason，尚非可直接部署的完整核验器。

| 当前任务 | 正式结果 | 独立审计 |
|---|---|---|
| 019：支持边界筛查 | [主报告](outputs/019_support_boundary_screen/report.md) | [PASS，原门槛失败](reviews/019_support_boundary_screen.md) |
| 020：固定λ2确认 | [主报告](outputs/020_lambda2_patient_validation/report.md) | [PASS，development确认](reviews/020_lambda2_patient_validation.md) |
| 021：BGE本地化 | [主报告](outputs/021_bge_localization/report.md) | [PASS，严格等价FAIL](reviews/021_bge_localization.md) |
| 022：竞争感知校准 | [主报告](outputs/022_competition_aware_support_calibration/report.md) | [PASS，阶段A停止](reviews/022_competition_aware_support_calibration.md) |

阅读入口：[项目总览](docs/PROJECT_STATUS.md) · [API当前规则](docs/API_POLICY.md) · [环境与安全重放](docs/REPRODUCIBILITY.md) · [审计索引](reviews/README.md)。

022按模型分流：BGE继续硅基流动冻结缓存，Judge直接阿里云0731，不等待池耗尽；全任务累计80元。022已停止，不自动新增调用。历史报告／协议／旧CURRENT中的“待审、旧路由、患者余量、未改.gitignore”是冻结快照；当前状态以本页、PROJECT_STATUS和各任务CURRENT_STATUS为准。

基于 VeriFact-BHC 的患者级临床文本与电子病历记录一致性核验研究。

当前研究围绕临床文本事实核验展开：给定一份关于患者的临床文本，利用该患者已有的电子病历（EHR）记录判断文本中的陈述是否得到病历支持，并分析现有核验方法的失败模式及可能的改进方法。

---

## 1. Project Structure

```text
Research-VeriFact/
├── data/       # 原始数据及研究过程中产生的需要持久化存储的数据
├── docs/       # 外部参考资料、阅读笔记和历史研究资料
├── reviews/    # 独立审计意见、修订与结项记录
├── src/        # 可复用的正式代码
├── scripts/    # src代码的运行入口
├── tasks/      # 各项研究任务的设计与说明
├── outputs/    # 各项任务对应的运行结果，与tasks一一对应
├── environment.yml  # Conda 环境定义
└── tests/      # 自动化测试
```

### `data/`

研究数据。

当前建议的数据层级：

```text
data/
├── 00_raw/
└── 01_interim/
```

- `00_raw/`
  - 保存官方发布的原始数据。
  - 保持只读，不修改其中任何文件。
  - 当前 VeriFact-BHC 数据位于：

    `data/00_raw/verifact-bhc/1.1.0/`

  - 官方数据定义参见该目录中的 `README.md`；本地 release 的实际结构、覆盖及说明差异参见 [数据审计结果](outputs/001_dataset_audit/README.md)。

- `01_interim/`
  - 保存从原始数据生成的中间数据。
  - 包括表连接、筛选、格式转换、统计分析所需的派生数据等。
  - 可确定性生成的内容原则上应能够由原始数据和代码重新生成。
  - 对于外部模型/API 等无法保证完全重现的中间结果，应保留原始响应及必要的运行信息。

如以后确实需要区分更多稳定的数据层，再增加新的数据目录，不提前建立不需要的层级。

### `docs/`

外部研究资料与阅读笔记。

论文、补充材料等外部来源主要保存在：

`docs/sources/`

这里不保存程序运行结果。

| 资料 | 定位 |
| --- | --- |
| [数据集笔记](docs/数据集笔记.md)、[论文笔记](docs/论文笔记.md) | 用户原始学习笔记，保留原内容；核验结论以 001–003 正式成果为准 |
| [患者 5954 中文导读](docs/VeriFact-BHC_单病例中文导读_患者5954.md) | 早期教学案例，患者已纳入 003 探索组 |
| [动态切分提示词](docs/动态切分提示词.md) | 之前 Hospital-02 项目的经验记录，不是当前 VeriFact 的方法或实验成绩 |
| `docs/sources/verifact_upstream_f115d36cb65f/` | 002 下载的作者代码参考快照；来源为 philipchung/verifact，固定提交和文件哈希见目录内 source_manifest.json 与 additional_source_manifest.json，未执行其模型或分析脚本 |

### `reviews/`

保存 [独立审计记录及后续状态](reviews/README.md)。原审计意见、执行者修订自查、用户确认结项分别记录；任务完成不意味着数据异常已消失，也不等于新增医学裁决。

### `src/`

项目的可复用代码。

正式实现的数据读取、检索、核验、评价等逻辑应逐步放入 `src/`，而不是长期堆积在单个脚本中。

当前已采用 Python 包结构：

```text
src/
└── verifact_research/
    ├── audit/       # VeriFact-BHC 数据审计
    └── evaluation/  # baseline 与新方法共用的评价及论文复算
```

审计入口为 `scripts/audit_dataset.py`，关键逻辑测试位于 `tests/test_dataset_audit.py`。

### `scripts/`

项目的运行入口。

例如：

- 数据检查；
- 数据预处理；
- 运行模型；
- 执行检索；
- 计算评价指标；
- 生成分析结果。

`scripts/` 中的代码应尽量调用 `src/` 中的实现，而不是重复实现核心逻辑。

### `tasks/`

记录研究过程中相对独立的工作任务。

当前任务目录按执行顺序编号：

```text
tasks/
├── 001_dataset_audit/
├── 002_reproduce_paper_results/
├── 003_error_analysis/
├── 004_event_alignment_pilot/
└── ...
```

这里的 `task` 不要求一定是论文中的“实验”。

数据核验、探索性分析、baseline、错误分析、方法实验和消融实验都可以作为独立 task。

每个 task 可以包含自己的 `README.md`，特别简单的可以不写，用于记录：

- 为什么进行这项任务；
- 要回答什么问题；
- 使用什么输入；
- 计划采用什么方法；
- 如何评价；
- 当前状态；
- 得到了什么结论。

任务编号一旦建立，不因任务失败、废弃或研究方向变化而重新编号。

### `outputs/`

保存各 task 实际产生的结果。

`tasks/` 和 `outputs/` 使用相同的编号和名称，一一对应：

```text
tasks/
└── 003_error_analysis/

outputs/
└── 003_error_analysis/
```

如果同一个 task 被运行多次，应保留不同运行记录，避免覆盖历史结果，例如：

```text
outputs/
└── 003_error_analysis/
    ├── run_001/
    │   └── review_004/  # 现行修订报告；此前 review 也保留
    ├── run_002/
    │   └── review_003/  # 同一修订的重复生成结果
    └── verification_003/
```

每次正式运行应尽可能保留能够复现该结果的信息，例如：

- 实际运行参数；
- 模型及版本；
- 输入数据版本；
- 随机种子；
- predictions；
- metrics；
- logs。

### `tests/`

项目自动化测试。

用于检查重要的数据处理逻辑、评价指标和公共函数，防止后续修改代码时无意改变已有行为。

---

## 2. Data Rules

### Raw data is immutable

`data/00_raw/` 中的官方数据不得直接修改。

需要清洗、筛选、合并或增加字段时，应生成新的派生文件，而不是覆盖原始数据。

### Derived data should be reproducible

研究过程中生成的数据原则上应能够根据以下内容重新构建：

1. 原始数据；
2. 当前代码；
3. 对应配置或参数。

### Use relative project paths

代码中不要写死：

`D:\Research-VeriFact\...`

应尽量使用相对于项目根目录的路径，使项目迁移到其他位置后仍然可以运行。

---

## 3. Task and Output Convention

一个研究工作如果值得单独记录其目的、输入、过程或结果，就可以建立一个 task。

任务编号示例（完整当前状态见第5节）：

```text
001_dataset_audit
002_reproduce_paper_results
003_error_analysis
004_event_alignment_pilot
```

004 已完成真实执行、独立审计及修订定向复核（2026-09-14 PASS），具备正式冻结／结项条件；结果方向不一致与执行遵守有限等研究边界继续保留。

无需判断它是否属于严格意义上的“实验”。

对应输出使用完全相同的名称：

```text
tasks/003_error_analysis/
outputs/003_error_analysis/
```

`tasks/` 记录“为什么做、准备怎么做”。

`outputs/` 记录“实际跑出了什么”。

---

## 4. Current Dataset

当前主要数据集：

**VeriFact-BHC v1.1.0**

位置：

`data/00_raw/verifact-bhc/1.1.0/`

主要数据包括：

- BHC propositions；
- clinician verdicts；
- proposition validity annotations；
- patient reference EHR；
- VeriFact model verdicts；
- retrieved reference contexts；
- model / retrieval configuration metadata。

官方定义参见 [release README](data/00_raw/verifact-bhc/1.1.0/README.md)。实际文件与说明存在部分差异，已在 [数据审计报告](outputs/001_dataset_audit/run_006/report.md) 中分别标明官方声明、独立验证结果和待确认事项。

---

## 5. Current Status

032已快速独立审计PASS：双粒度主方案PA略升但MCC下降、false-S增加，未实现共同提高，不改选辅助方案、不自动033。031已快速独立审计PASS：扩充未带来实质确认增量，停止当前新增信息Gate，A仅作简单参照，不自动032。030已快速独立审计PASS：训练规模有积极线索，组成敏感性未解决，不能确定稳定最低人数，不自动扩量或031。029已快速独立审计PASS：保留联合信息的有限OOF增量，迁移未稳定复现，不选winner、不自动030。028已快速独立审计PASS：trace仅保留44/110真S救回，未过门槛，停止当前版本，不自动029。027离线诊断已快速独立审计PASS：高rescue区不能只靠换阈值恢复原门槛，现有证据不支持继续救当前Gate。026结论保持：冻结SD跨患者组迁移未达事前门槛，停止当前版本。025此前结论保持：E路线停止，第二Judge仅保留有限开发线索，完整门槛无winner。024已完成跨后端/模型开发验证；均方向支持、未达强证据门槛。固定λ2保持，reserved40未开启。022此前按阶段A门槛停止，023完成零API敏感性分析。此前021已完成两个BGE的本地化与API→本地冻结等价性检查；严格等价门槛FAIL，因此020的科学结果仍属于原API-BGE实现条件，不能自动继承到本地链路。001–032均有相应独立审计依据。40名development均已用于开发/确认；021仅复用020冻结development输入，40名reserved test继续保留，是否开启最终测试及采用API还是本地BGE需另行冻结决策。

| 任务 | 状态 | 说明与结果 |
| --- | --- | --- |
| `001_dataset_audit` | 已完成（2026-09-12） | [任务说明](tasks/001_dataset_audit/README.md) · [正式结果入口](outputs/001_dataset_audit/README.md) |
| `002_reproduce_paper_results` | 已完成（2026-09-13） | [任务说明与统一协议](tasks/002_reproduce_paper_results/README.md) · [正式结果入口](outputs/002_reproduce_paper_results/README.md) |
| `003_error_analysis` | 已完成并确认结项（2026-09-13） | [任务说明](tasks/003_error_analysis/README.md) · [结果入口](outputs/003_error_analysis/README.md) |
| `004_event_alignment_pilot` | 已完成，修订独立复核 PASS，可冻结／结项（2026-09-14） | [任务说明](tasks/004_event_alignment_pilot/README.md) · [中文主报告](outputs/004_event_alignment_pilot/run_003/analysis/report.md) |
| `005_pilot_effect_analysis` | 已通过独立审计（2026-09-14；见 reviews/005） | [任务说明](tasks/005_pilot_effect_analysis/README.md) · [简明中文主报告](outputs/005_pilot_effect_analysis/run_002/review_002/report.md) |
| `006_source_context_feasibility` | 已通过精简独立审计（2026-09-14；见 reviews/006） | [任务说明](tasks/006_source_context_feasibility/README.md) · [简明中文主报告](outputs/006_source_context_feasibility/run_001/review_001/semantic_001/report.md) |
| `007_context_retrieval` | 已通过精简独立审计（2026-09-14；见 reviews/007） | [任务说明](tasks/007_context_retrieval/README.md) · [简明中文主报告](outputs/007_context_retrieval/run_001/review_001/semantic_001/report.md) |
| `008_retrieval_planning` | 已通过精简独立审计（2026-09-14；见 reviews/008） | [任务说明](tasks/008_retrieval_planning/README.md) · [简明中文主报告](outputs/008_retrieval_planning/run_001/report.md) |
| `009_retrieval_baselines` | 修订独立复核 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/009_retrieval_baselines/README.md) · [简明中文主报告](outputs/009_retrieval_baselines/report.md) |
| `010_verifact_baseline_alignment` | 精简独立审计 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/010_verifact_baseline_alignment/README.md) · [简明中文主报告](outputs/010_verifact_baseline_alignment/report.md) |
| `011_evidence_integrity_packaging` | 执行完成，pilot未过继续门槛；独立审计PASS，可结项 | [任务说明](tasks/011_evidence_integrity_packaging/README.md) · [中文主报告](outputs/011_evidence_integrity_packaging/report.md) |
| `012_comparative_error_diagnosis` | 独立审计 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/012_comparative_error_diagnosis/README.md) · [中文主报告](outputs/012_comparative_error_diagnosis/report.md) |
| `013_multi_mechanism_screen` | 独立审计PASS，四分支停止，可结项 | [任务说明](tasks/013_multi_mechanism_screen/README.md) · [中文主报告](outputs/013_multi_mechanism_screen/report.md) |
| `014_qwen27b_baseline_comparison` | 修订独立复核PASS，可冻结／结项 | [任务说明](tasks/014_qwen27b_baseline_comparison/README.md) · [中文主报告](outputs/014_qwen27b_baseline_comparison/report.md) |
| `015_disagreement_adjudication` | 修订独立复核PASS，无winner，停止并结项 | [任务说明](tasks/015_disagreement_adjudication/README.md) · [中文主报告](outputs/015_disagreement_adjudication/report.md) |
| `016_disagreement_triggered_review_validation` | 快速独立审计PASS，未达门槛，停止并结项 | [当前任务入口](tasks/016_disagreement_triggered_review_validation/CURRENT.md) · [中文主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md) · [独立审计](reviews/016_disagreement_triggered_review_validation.md) |
| `017_verification_supervised_evidence_utility` | 快速独立审计PASS；第一阶段未达门槛，停止 | [任务](tasks/017_verification_supervised_evidence_utility/README.md) · [中文主报告](outputs/017_verification_supervised_evidence_utility/report.md) · [独立审计](reviews/017_verification_supervised_evidence_utility.md) |
| `018_verifact_gap_attribution` | 快速独立审计PASS；离线诊断结项 | [任务](tasks/018_verifact_gap_attribution/README.md) · [中文主报告](outputs/018_verifact_gap_attribution/report.md) · [独立审计](reviews/018_verifact_gap_attribution.md) |
| `019_support_boundary_screen` | 第一阶段完成，原低代价保护门槛未通过；快速独立审计PASS | [任务](tasks/019_support_boundary_screen/CURRENT_STATUS.md) · [中文主报告](outputs/019_support_boundary_screen/report.md) |
| `020_lambda2_patient_validation` | 固定λ=2新10名development患者双轮验证完成；总体PA/MCC复现改善，快速独立审计PASS | [任务](tasks/020_lambda2_patient_validation/CURRENT_STATUS.md) · [中文主报告](outputs/020_lambda2_patient_validation/report.md) · [统计附录](outputs/020_lambda2_patient_validation/statistics.md) |
| `021_bge_localization` | 两个BGE本地化完成；严格API→本地冻结等价FAIL，快速独立审计PASS | [任务](tasks/021_bge_localization/CURRENT_STATUS.md) · [中文主报告](outputs/021_bge_localization/report.md) · [当前状态](outputs/021_bge_localization/CURRENT_STATUS.md) |
| `022_competition_aware_support_calibration` | 阶段A停止；快速独立审计PASS | [任务](tasks/022_competition_aware_support_calibration/CURRENT_STATUS.md) · [报告](outputs/022_competition_aware_support_calibration/report.md) · [独立审计](reviews/022_competition_aware_support_calibration.md) |
| `023_lambda_boundary_response_analysis` | 离线响应分析完成；快速独立审计PASS；λ=2不变 | [任务](tasks/023_lambda_boundary_response_analysis/CURRENT_STATUS.md) · [报告](outputs/023_lambda_boundary_response_analysis/report.md) · [图](outputs/023_lambda_boundary_response_analysis/README.md) |
| `024_lambda2_transfer_validation` | 快速独立审计PASS；方向支持，未达强迁移证据门槛 | [任务](tasks/024_lambda2_transfer_validation/CURRENT_STATUS.md) · [报告](outputs/024_lambda2_transfer_validation/report.md) · [审计](reviews/024_lambda2_transfer_validation.md) |
| `025_lambda_flip_risk_separability` | 快速独立审计PASS；E停止，完整门槛无winner | [任务](tasks/025_lambda_flip_risk_separability/CURRENT_STATUS.md) · [报告](outputs/025_lambda_flip_risk_separability/report.md) · [审计](reviews/025_lambda_flip_risk_separability.md) |
| `026_frozen_sd_patient_transfer` | 快速独立审计PASS；冻结SD未达迁移门槛，停止 | [任务](tasks/026_frozen_sd_patient_transfer/CURRENT_STATUS.md) · [报告](outputs/026_frozen_sd_patient_transfer/report.md) · [审计](reviews/026_frozen_sd_patient_transfer.md) |
| `027_dual_judge_transfer_diagnosis` | 快速独立审计PASS；离线诊断结束，026停线保持 | [任务](tasks/027_dual_judge_transfer_diagnosis/CURRENT_STATUS.md) · [报告](outputs/027_dual_judge_transfer_diagnosis/report.md) · [审计](reviews/027_dual_judge_transfer_diagnosis.md) |
| `028_traceable_claim_evidence_verification` | 快速独立审计PASS；可追溯核查未过门槛，停止当前版本 | [任务](tasks/028_traceable_claim_evidence_verification/CURRENT_STATUS.md) · [报告](outputs/028_traceable_claim_evidence_verification/report.md) · [审计](reviews/028_traceable_claim_evidence_verification.md) |
| `029_semantic_information_gate` | 快速独立审计PASS；保留OOF信号，迁移未稳定，不选winner | [任务](tasks/029_semantic_information_gate/CURRENT_STATUS.md) · [报告](outputs/029_semantic_information_gate/report.md) · [审计](reviews/029_semantic_information_gate.md) |
| `030_gate_training_stability` | 快速独立审计PASS；规模有积极线索，组成敏感性未解决，不自动扩量 | [任务](tasks/030_gate_training_stability/CURRENT_STATUS.md) · [报告](outputs/030_gate_training_stability/report.md) · [审计](reviews/030_gate_training_stability.md) |
| `031_training_expansion_confirmation` | 快速独立审计PASS；扩充未确认实质增量，停止当前新增信息Gate | [任务](tasks/031_training_expansion_confirmation/CURRENT_STATUS.md) · [报告](outputs/031_training_expansion_confirmation/report.md) · [审计](reviews/031_training_expansion_confirmation.md) |
| `032_evidence_relation_correction` | 快速独立审计PASS；主方案未实现PA/MCC共同提高，不改选辅助方案 | [任务](tasks/032_evidence_relation_correction/CURRENT_STATUS.md) · [报告](outputs/032_evidence_relation_correction/report.md) · [审计](reviews/032_evidence_relation_correction.md) |

审计代码、机器结果、原始文件校验和重复运行验证均已完成。审计保留了实际数据异常，其中两条医生第二轮记录触发一致性检查失败；任务完成不表示所有数据检查通过。详细异常和适用范围统一记录在审计结果中。

002 对 426 个模型/实验组合重评分，72 项核心点估计与论文一致；R1-70B 主配置的 MCC 置信区间仍有差异，正式附录部分未确认。两次完整运行的 37 个机器文件一致；002 完成时的 30 项测试与公共评价入口回放通过。

后续 baseline 和新方法统一使用 `scripts/evaluate_predictions.py` 与 `verifact_research.evaluation.evaluate`。默认 valid-only、固定队列、完整预测、三分类 PA/AC1/MCC 和患者 bootstrap；论文保留 invalid 的 item bootstrap 口径单独维护。具体样本与参数以 002 协议为准。

003 在 20 名探索患者的 1,817 条有效 atomic claims 中分层查看了 24 例，保留 40 名后续开发与 40 名测试患者。修订版 review_004 将观察收紧为事件对应和支持充分性问题；H03 撤回遗漏时间归因，H04 补充术语／检查对应及输入中已有异常信息。原 24 例的 R1 完整输出已复查，仍保留无法确定原因的病例；修订者自查完成，用户确认本任务结束。后续独立定向复核已 PASS，H03 阻塞项关闭，见 [003 审计末尾记录](reviews/003_error_analysis.md)；没有新增医生裁决。首个假设已完成004 pilot；003原第二个实验未按原方案单独执行，相关证据利用问题已在005–009继续分析，不是当前自动待办。003观察仍非已验证的方法贡献。

正式阅读入口分别为 001 的 `run_006`、002 的 `run_003`、003 的 `run_001/review_004`、004 的 `run_003/analysis/report.md`。003 完成时全项目 42 项测试通过，记录见 [003 verification_003](outputs/003_error_analysis/verification_003/verification.json)。004 离线准备时 54 项测试通过，记录见 [004 verification_001](outputs/004_event_alignment_pilot/verification_001/verification.json)。004 真实运行的执行自查、原始回执重复评价和测试见 [verification_live](outputs/004_event_alignment_pilot/verification_live/run_001/verification.json)，不等同于独立审计。004 修订后的独立复核见 [审计文末结论](reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)：81 项现有测试通过、41 项隔离篡改检查通过，两次离线重放的 15 个结果文件均与原结果逐字节一致。

后续任务复用冻结的患者分组清单，不重新抽组。baseline 和新方法继续使用 002 的同一评价代码。任务结束后，001 的数据异常、002 的论文差异和代码使用限制、003 的探索性结论边界仍保留，详见 [审计与后续状态](reviews/README.md)。

---

## 6. Development Environment

项目使用 Conda 环境 `research-verifact`（Python 3.11），环境定义见 `environment.yml`。

```powershell
conda env create -f environment.yml
conda activate research-verifact
```

已有环境可用 `conda env update -f environment.yml` 同步依赖。

029–031使用独立research-verifact-029环境，版本冻结见其preparation_001/environment.json；原环境未改。当前计算环境支撑001–028的数据处理、评价和既有回执重放；021本地GPU环境另见[environment.local-bge.yml](environment.local-bge.yml)及[复现说明](docs/REPRODUCIBILITY.md)。DuckDB 读取数据，pypdf 读取论文，fonttools 保留为 001 已登记的字体编码核对工具，NumPy/pandas/SciPy/scikit-learn/irrCAC 支持计算及指标交叉核验。003、004 复用现有依赖，没有新增模型推理包；版本以 `environment.yml` 为准。001–003 的日常重跑及 004 离线准备、已保存响应重评分不需要 GPU 或推理 API。004 真实推理由 Python 标准库 urllib 调用硅基流动，无新增依赖；虚构服务 preflight 也会真实调用 API。

2026-09-14 状态同步核对：Python 为 3.11.16，8 个固定依赖版本均与环境定义一致，`python -m pip check` 通过。004 的 SiliconFlow 请求仅使用标准库，当前环境没有 Groq 专属依赖，不新增包或升级版本，`environment.yml` 无需变化。fonttools 虽未被当前解析函数直接导入，仍由 001 runner 查询并记录其版本，因此本轮不移除这一已登记依赖。重新渲染 002 的来源核对 PNG 另需 Poppler 的 `pdftoppm`，不属于日常重跑依赖，见 [来源核对说明](outputs/002_reproduce_paper_results/source_review/README.md)。

---

## 7. Run Dataset Audit

从项目根目录、已激活的 `research-verifact` 环境运行：

```powershell
python -B scripts/audit_dataset.py
python -B -m unittest discover -s tests -v
```

审计创建新的 `outputs/001_dataset_audit/run_XXX/`，保留历史结果。当前 release 的第二轮医生字段矛盾会使审计返回非零退出状态，完整结果仍会生成，manifest 标为 `failed_checks`；运行异常则标为 `error`。具体检查与参数见 [任务说明](tasks/001_dataset_audit/README.md)。

---

## 8. Reproduce Paper Results and Evaluate Methods

```powershell
python -B scripts/reproduce_paper_results.py
python -B scripts/evaluate_predictions.py --help
```

论文复算使用已有 release 预测，不调用推理服务，每次创建新的 002 run。baseline / 新方法评价 CSV 格式、完整命令、缺失处理和配对比较见 [002 任务说明](tasks/002_reproduce_paper_results/README.md)。

---

## 9. Review Error Analysis Results

003 已结项，先阅读 [结果入口](outputs/003_error_analysis/README.md) 或 [现行报告](outputs/003_error_analysis/run_001/review_004/report.md)。

核对已保存的两份修订成果、原始文件哈希、链接和现有测试：

```powershell
python -B tasks/003_error_analysis/verify.py
```

该命令新建 verification 记录，不重新抽患者或调用模型。重新生成报告的命令、review 序号和完整输出阅读范围见 [003 任务说明](tasks/003_error_analysis/README.md)。

---

## 10. Event Alignment Pilot Results

004 按冻结顺序使用 6 名开发患者、421 条有效 atomic claims，三臂由硅基流动 `deepseek-ai/DeepSeek-V4-Flash` 使用同一完整 reference 生成。1,263 个逻辑请求均已处理，1,262 个有效预测，另有 1 个 LLM routine 截断失败；对应 routine 比较受阻。核心 event_alignment − structured 使用完整 181/240 分母，MCC 差值分别为 +0.0425/-0.0416，患者 bootstrap 区间均跨 0。检查结构遵守有限，不建议直接扩大当前版本。AWS Bedrock / Groq 已放弃，不是当前待办。真实推理按 usage 和公开日期价格估算约 ¥30.326；用户反馈本轮消耗约 30 元额度，尚未逐笔核对账单。后续实验须控制输入 token 与调用成本。

```powershell
python -B tasks/004_event_alignment_pilot/analyze_live.py --run outputs/004_event_alignment_pilot/run_003 --output outputs/004_event_alignment_pilot/replay_local --no-report
python -B tasks/004_event_alignment_pilot/verify_live.py --run outputs/004_event_alignment_pilot/run_003
```

以上命令只重放本地记录，不发送临床内容，输出目录须不存在。直接阅读 [004 中文主报告](outputs/004_event_alignment_pilot/run_003/analysis/report.md)；配置、服务恢复、评价处理与机器资料见 [004 任务说明](tasks/004_event_alignment_pilot/README.md) 和 [输出索引](outputs/004_event_alignment_pilot/README.md)。历史 run_001/run_002 离线准备保留。当前修订已通过 [独立定向复核](reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)，两项原问题关闭，可正式冻结／结项。执行者的修订、自查和交审版本保存在 [历史修订说明](outputs/004_event_alignment_pilot/verification_live/run_002/README.md)。旧报告、status.json 和 verification 中的“等待审计／复核”保留其生成时状态，当前状态以本入口和审计末尾追加结论为准。后续 API 费用确认按 [当前规则](AGENTS.md#api-调用费用与确认规则)：一次新任务预估总费用不超过 80 元可直接执行，超过则先确认；历史 run 的授权与预算保留原记录。

## 11. API账号、平台与费用（现行）

执行前读取[API_POLICY.md](docs/API_POLICY.md)和[AGENTS费用规则](AGENTS.md#api-调用费用与确认规则)。新任务默认80元累计保护；≤80元直接执行，超过或无法合理估算先确认，跨模型、账号、供应商、阶段和重试累计。

后续收费API（含V4/Qwen）先使用硅基流动启用号池，从account_2起按编号换号。所有启用硅基流动账号明确额度耗尽后，通知用户并永久记录此次转换，后续全部API工作转阿里云，除非用户另有指示。超时／503不当作额度耗尽，目前未确认全部耗尽。

本地密钥位置：`.env.siliconflow_pool`与`.env.aliyun`，现有.gitignore已排除，勿提交或打印。配置与实现边界见[硅基流动说明](docs/siliconflow_pool/README.md)、[阿里云当前说明](docs/aliyun/CURRENT.md)。单次工具、历史runner和研究任务的冻结预算须区分；旧016的40元硬保护及全部回答不改写，新任务另行登记80元上限。此次同步不调用API、不查询余额、不重新启动历史任务。

以下第12–23节回顾各任务形成时的发现与建议，不是新的执行授权；当前状态以顶部总览和审计索引为准。

## 12. Pilot Effect Analysis

005 对 004 全部 421 条进行转移统计，并深入阅读 25 个改善、退化、仍错及稳定对照病例。两臂指标未变化，没有新推理；观察涉及命题要求、证据利用、标签边界及来源上下文中的事件/剂量指代。005当时建议验证局部来源上下文与EHR证据的角色区分，006已完成该验证且未证明净收益；不作为新的待执行实验。阅读 [唯一中文主报告](outputs/005_pilot_effect_analysis/run_002/review_002/report.md)；104 项测试、重复提取/渲染及 265 处锚点自查见 [结果入口](outputs/005_pilot_effect_analysis/README.md)。

## 13. Source Context Feasibility

006 在用户批准的 8 元上限内完成 64 条命题、三臂 192 次实际尝试，189 条有效预测；2 次通信未知和 1 次截断未重发、未补标签。两个作者的主比较均受缺失阻塞，human 来源−重复对照 ΔMCC +0.0326、区间跨 0，且 NS/NA 召回下降。深读 28 例后建议修改切入点，先考察固定命题下 EHR 证据来源/时段与支持范围，不直接扩大当前 BHC 上下文版本。费用与未知预留约 ¥3.8661；116 项离线测试、已有回执重放及 316 处锚点自查见 [006 结果入口](outputs/006_source_context_feasibility/README.md)，主报告为 [report.md](outputs/006_source_context_feasibility/run_001/review_001/semantic_001/report.md)。005 最新独立结论以 [005 审计](reviews/005_pilot_effect_analysis.md) 为准，原报告保留历史状态。

## 14. Context-aware Retrieval

007 使用四名新的开发患者、96 条固定有效 claim，比较 BM25 的 claim、来源句、局部来源、claim＋局部来源融合查询；最终 Judge 仅收到原 claim 和 EHR。392 次主试验/重复对照及 12 次零预算边界补充均有效，累计估算 ¥4.1703。主 mixed−claim ΔMCC 为 LLM +0.0089、human −0.0718，两个患者区间均跨 0；真实召回改善与同输入 Judge 波动、查询偏离及证据截取问题并存。007当时建议改进候选召回/组织及原claim重排；008–013已开展后续对照，不能把该建议当新的自动待办。阅读 [唯一中文主报告](outputs/007_context_retrieval/run_001/review_001/semantic_001/report.md)；124 项断网测试、回执重放及 377 处锚点自查见 [结果入口](outputs/007_context_retrieval/README.md)。006 最新独立结论见 [精简审计](reviews/006_source_context_feasibility.md)，历史报告保留生成时状态。

## 15. LLM Retrieval Planning

008 在六名新开发患者的 144 条固定 claim 上比较 direct、简单来源扩展和 LLM planner，共用 BM25＋BGE-M3、原 claim rerank 和普通 structured Judge。三臂各 144 条有效预测，311 个实际 Judge 请求（含 12 次无翻转重复），全部服务共 684 次，usage 估算 ¥4.1528＜¥40。Planner−direct 的 ΔMCC 为 LLM +0.0176、human 0，区间均跨 0；100 个计划使用、44 个退回，接口损耗不均衡。20 例完整阅读表明局部证据补充与丢失并存，008当时建议检查候选融合/证据覆盖和Judge支持边界；009–013已进一步检验，当前仍不扩大通用planner。阅读 [唯一中文主报告](outputs/008_retrieval_planning/run_001/report.md)；离线重建、费用、79 处锚点和准确交审版本见 [结果入口](outputs/008_retrieval_planning/README.md)。007 的当前独立状态以 [精简审计](reviews/007_context_retrieval.md) 为准，历史报告不回写。

## 16. Retrieval Baselines and Evidence Loss

009先用008旧患者开发，再冻结A48（BM25+dense RRF）、B48（dense）和C48（两路交替保留48候选），在原开发顺序第19–24名患者全部650条valid claim确认。三臂共享原claim重排、Judge与证据上限，均完整。C−A的LLM/human ΔMCC为+0.0002/+0.0158，未证明稳定优势；B在人写组净少判对20条。证据损失同时出现于候选门槛、每note限制、字符容量和Judge解释；这是009当时的后续研究依据，010–013已完成相关校准与筛选，当前不继续原样扩大。全任务usage估算¥18.0822＜¥40；首次自查143项测试通过，修订后146项通过，原回执重放不变。阅读[唯一主报告](outputs/009_retrieval_baselines/report.md)及[成果与当前审计状态](outputs/009_retrieval_baselines/README.md)，自查不等于独立审计。008当前独立结论以[审计记录](reviews/008_retrieval_planning.md)为准，历史报告保留原状态。

009当前状态以[独立审计末尾追加](reviews/009_retrieval_baselines.md)为准：146项断网测试、109个内容文件重放及冻结材料负向检查通过；旧报告、自查和交审说明保留当时状态。

## 17. 010 baseline校准（精简独立审计PASS，可结项）

010 已完成同队列发布系统参考及同期同Judge的reference校准，2026-09-15精简独立审计PASS，可冻结／结项；沿用009的650条命题，没有新患者。发布reference−C48的LLM/human ΔMCC为−0.0572/−0.0497，两个区间跨0，human PA/AC1区间倾向C48；发布系统较高PA不能直接归因于检索。保留C48作实用对照，010当时建议单独验证检查身份、条件句和时间/状态完整性；尚未证明packaging有效。主报告见[010成果入口](outputs/010_verifact_baseline_alignment/README.md)，独立结论见[010审计记录](reviews/010_verifact_baseline_alignment.md)，历史报告保留交审时状态。

同期两臂各650条有效预测，预设重复24次中2次翻转；旧009→010相同C48完整输入有80/650条标签变化，不能将跨运行变化当reference收益。全任务usage估算¥23.3621，未知请求保留¥0.1050，总已用/预留¥23.4671＜¥40，非账单。150项断网测试通过，009的3317个历史文件未变。010未更改C48、Judge或开发包装方法；全部调用停止，独立审计已通过，研究限制保留。

## 18. 011证据完整性验证（精简独立审计PASS，可冻结／结项）

011在既有任务基础上完成650条离线完整性/预算检查和固定24条三臂三次诊断，2026-09-15精简独立审计PASS，可冻结／结项；预设继续门槛未通过，650条main未启动。011的C−B三轮净正确数为−1/0/0、B−A为−2/0/0，停止当前B/C组合扩展，不把B整体改作新性能baseline。继续保留冻结C48作为实用对照；基本完整性确有修复，但未证明额外结构恢复有重复净收益。011当时40名开发只使用前24名，剩余16名及40名reserved test未用于011。当前入口：[011主报告](outputs/011_evidence_integrity_packaging/report.md)与[交审说明](outputs/011_evidence_integrity_packaging/audit_handoff.md)。

实际195个有效请求、usage估算¥1.2874。较完整的证据可伴随预算挤占，Judge的支持范围/NS-NA边界和重复波动仍明显。未将已发现的真实原文修复包装为方法有效；未启动main，后续012/013已开展诊断与机制筛选，当前仍不续跑011 main。

011当前独立结论见[审计记录](reviews/011_evidence_integrity_packaging.md)；原报告与交审快照保留当时状态。

## 19. 012对照错误诊断（独立审计PASS，可结项）

012_comparative_error_diagnosis 已完成离线执行并通过2026-09-15独立审计，可冻结／结项；[唯一主报告](outputs/012_comparative_error_diagnosis/report.md)。复用010同650条三组材料，错误并集195、固定深读24例（19条错误、5条三组共同正确），其余176条错误本轮未深读；0 API、无新患者。新增观察是本地极性/候选/打包损失与原/现系统共同的目标及支持范围问题并存，不能把正确标签或模型解释当机制证明。012建议优先验证目标/支持范围约束，极性与条件保真作为窄工程前提；保留冻结C48对照，不直接采用011 B或继续其main。建议有诊断依据但不是已证实优化收益。

012当前独立结论见[审计记录](reviews/012_comparative_error_diagnosis.md)：无阻塞项，可冻结／结项。原报告／交审快照保留当时状态；阅读缓存是保留metadata、空白规范化后相同正文的复用，并非所有块逐字节相同。

## 20. 013多机制筛选（独立审计PASS，可结项）

013_multi_mechanism_screen 已完成执行并通过2026-09-15快速独立审计，可冻结／结项；[唯一主报告](outputs/013_multi_mechanism_screen/report.md)。四个分支通过局部机制检查，但在固定231条压力集相对同期冻结C48的净正确数分别为：主谓合同−12、前缀修复−4、扩候选−5、LLM集合选择−5，均未通过预设门槛。停止当前四个实现的扩大，不默认组合；没有新患者确认或新论文方法候选。保留C48作既有实用对照，013当时剩余16名development与40名reserved test未用于013。全任务估算/预留¥18.8002，全部API已停止；局部作用、原文质量要求与整体性能结论应分开。

## 21. 014固定证据模型比较（修订独立复核PASS）

旧6名开发患者650条，同C48和structured，Qwen与010已有V4比较；两者非同期。Qwen可保留为较小模型研究对象，但human NA较弱，未证明非劣或本地部署性能。见[主报告](outputs/014_qwen27b_baseline_comparison/report.md)及[审计](reviews/014_qwen27b_baseline_comparison.md)。

## 22. 015双候选理由仲裁（修订独立复核PASS，停止）

主仲裁523/650，比最强单模型527净−4；evidence_only对照542只是探索性正向信号，后由016验证。015没有winner，不追加v2/v3；候选顺序偏差保留。见[主报告](outputs/015_disagreement_adjudication/report.md)及[审计](reviews/015_disagreement_adjudication.md)。

## 23. 016分歧触发独立复核（独立审计PASS，停止）

新6名开发患者601条，92条分歧；review452，低于Qwen457，只比普通repeat451多1条。原继续门槛未通过，human NA及患者保护亦有损失；停止当前方向，不以局部MCC提升挽救。未使用余下10名开发患者或reserved test确认。Qwen混合供应商、基础模型跨时段，限制保留。见[当前成果入口](outputs/016_disagreement_triggered_review_validation/CURRENT.md)、[主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)及[审计](reviews/016_disagreement_triggered_review_validation.md)。

## 24. 017医生verdict监督的证据utility（第一阶段停止，独立审计PASS）

017完成12名已暴露患者192条GT盲证据干预：19条稳定错误中稳定救回0条，160条稳定正确中破坏3条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。有限单段替换结果不是全局selection不可能性的证明。1572份有效回答，累计费用估算与未知预留¥13.37319060/¥80；原始回执、失败与历史001–016保持。见[017中文主报告](outputs/017_verification_supervised_evidence_utility/report.md)。
