# 选择性临床核验：定向文献结论（2026-10-31）

**值得做有上限的风险—工作量可行性分析；目前不能承诺formal guarantee，更不能把拒答后准确率当原生三分类提升。** 有同类临床应用和成熟理论，但“LoRA＋CP”本身已不是新方法。可辩护价值应来自：同一临床核验任务、医生原GT、相同模型/证据/评价ID，在相同自动覆盖率或人工复核量下，确实降低错误放行，并完整交代代价。发表载体只能证明方向有人研究，不能保证SCI分区、EI收录或录用。

## 用户提到的两篇：均找到，但保证不能照抄

1. **[Kim等，AAAI Fall Symposium Series，2025](https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929)**，题目为 *Conformal Prediction and Verification of Large Language Model Extractions in EHR Data*，7(1):539–546。与记忆精准匹配：真实EHR的实体抽取＋LLM核验＋拒绝/人工复核；不是单纯一般CP。10,000次就诊、3,012名帕金森病相关患者、898诊所；另用VeriFact-BHC检查agreement。并非主会AAAI论文。
2. **[Fu等，Scientific Reports，2026](https://www.nature.com/articles/s41598-026-66677-w)**，*Risk-aware multiple-choice question answering with conformal P-values*，16:27227。匹配期刊/年份/CP，但任务是MMLU/MMLU-Pro选择题，**不是临床EHR核验**。α=.1时平均集合大小约2.01–2.89、6.39–7.94；集合覆盖不等于能自动回答的比例，更不等于接受部分低错误率。

**AAAI方法段的具体保留意见（不是据摘要否定整篇）：** 原文p.543 Eq.(3–5)使用生成token几何平均概率、`s=-logit(p)`、全部校准s的高分位数，并以`s≤τ`接受；写70%训练/30%校准。该分位数只约束s的尾部，本身未利用正确性标签来证明错误风险。Eq.(6)的`P(错误且接受)≤α`与其声称“等价”的Eq.(7)接受集合错误比例并不等价。Table4在α=.05时报告总拒绝率63.7%（标准）/42.6%（flex），不能概括为几乎全自动；独立测试如何与所谓62,981条test corpus的70/30拆分对应、Cov列如何对应宣称风险，当前片段未澄清。应保留其真实应用/校准异质性观察，避免继承过强定理。这是对当前可读方法段的保留意见，不是对全文的完整同行评审。

可复核入口：[官方PDF](https://ojs.aaai.org/index.php/AAAI-SS/article/download/36929/39067/41006)。直连受BotStopper限制，本次公式及Table4来自该**官方PDF搜索索引的正文片段**；未伪称拿到本地完整PDF。检索式：`"Conformal Prediction and Verification" "Category-specific conformal threshold" "τ"`；`"Conformal Prediction and Verification" "Table 4" "Brier"`。具体页码、条件与访问局限也记入sources.json。

## 四项补充原始来源

|来源|可以借鉴的内容|不能据此声称|
|---|---|---|
|[Conformal Risk Control，ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html)|交换性、有界单调loss、有限样本修正，控制平均风险|任意非单调的选择性错误比率都能直接套普通CRC|
|[Learn then Test，AOAS 2025](https://doi.org/10.1214/24-AOAS1998)|§3.2直接讨论拒答后的条件错误率；有效检验＋多重比较保护|在同一评价集反复挑阈值仍有原定保证；也不是ICLR2022论文|
|[Distribution-free, Risk-controlling Prediction Sets，JACM 2021](https://www.gsb.stanford.edu/faculty-research/publications/distribution-free-risk-controlling-prediction-sets)|独立校准、嵌套集合/单调风险、风险上置信界，区分α与δ|把经验风险≤α直接当总体风险证明|
|[Snyder/Brodsky，AJCP增刊2024](https://academic.oup.com/ajcp/article/162/Supplement_1/S171/7822986)|真实病理报告＋微调LLaMA-3B＋独立验证阈值；摘要称拒答30%后准确率95%→99.5%|它是增刊摘要；未给完整样本量/风险定理，不能当部署验证或LoRA专门证据|

## 本项目怎样做才可辩护

- 先明确目标：自动覆盖率、接受部分错误率、接受S中的错误比例、原全部non-S分母上的错误放行率是不同量。普通CP的`P(Y∈Γ)≥1−α`不能自动推出`P(错|单例集合)≤α`。理论需要明确目标；LTT的选择性分类部分比泛用CP包装更贴近。
- 阈值/模型/提示词必须先固定，校准和测试以患者隔离，并且不能用已参与模型训练/选型的数据冒称独立。当前8名内部验证患者还涉及107起点43条监督历史，且有多轮选型暴露；现在最多先做**回顾性**风险—覆盖描述，不能直接写新的部署保证。患者内多claim也不等于同量独立校准样本。
- 最小比较保留同一LoRA9B原判定；仅决定自动接受还是送审。比较无拒答、随机送审和简单max-score阈值，并在相同覆盖率报告风险曲线、S/NS/NA、患者/作者、实际推理成本和复核工作量。若更复杂方法没有优于简单阈值，就不增加组件。人工尚未实际复核时，只能报告送审命中/剩余风险，不能把医生GT代入当已完成的人工纠错成绩。

当前结论是“有研究价值，但需要先证明可用的风险—覆盖增量与合法校准数据”。不必新造算法，也不以PriorG改名、单点高准确率或文献的强保证措辞代替证据。该文献核对未实现Conformal系统、未调用付费API或GPU；143另有零新增推理的固定分歧送审回顾，见[基线结果](report.md)。
