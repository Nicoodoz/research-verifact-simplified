# 055：Zero-label Adaptation

## 核心结论

055的目标是：新环境target端完全没有GT，只凭无标签claims/model outputs自动适应，并尽量保持或提高PA、MCC、false-S与S/NS/NA recall。

**当前结果：部分做到，但未达到“跨新环境稳定提升”的正式目标。**

我们已经做到：
1. target 0标签估计类别prevalence（BBSE）；
2. target 0标签检测明显prevalence shift；
3. target 0标签选择/更新decision policy；
4. 在部分target/shift环境中，zero-label adaptation确实提高PA/MCC；
5. 通过完整Qwen second opinion获得了明显互补的NS信息。

但尚未做到：
> 同一个source-only选择规则，在052↔053及多种shift环境中都稳定优于Frozen PriorG，同时不明显牺牲false-S或任一少数类recall。

因此最终可部署的安全策略仍是Frozen PriorG + 无标签shift monitoring；055没有把未经目标标签确认的自动adaptation升为主系统。

## 1. Initial zero-label adaptation without new models

初始055使用Frozen PriorG、BBSE、shift detector和source-prevalence-conditioned policy。target GT从不进入适应过程。

自然052/053与source prior接近，因此detector正确地多数选择“不动”。在模拟shift中，DetectPA/DetectMCC在high-S或部分NA-heavy条件可提升PA，但在S70、S60、NS-heavy以及target=053的多个条件上降低PA/MCC或少数类recall。即使增加source-domain robust guard，也只能在部分target保持Frozen，不能形成跨域稳定增益。

连续score-distribution/GMM式无标签adaptation也失败：target伪标签更新会放大类条件分布误差，PA/MCC明显低于PriorG。

因此仅靠prevalence估计和DeepSeek score geometry，zero-label automatic update没有达标。

## 2. Full Qwen second opinion extension

为增加与DeepSeek不同的错误信息源，055按Protocol Amendment 001补全Qwen3.8-27B non-thinking scoring：

- 052：240条，22条复用既有Qwen，218条新调用；
- 053：240条，29条复用，211条新调用；
- 新调用429/429完成；
- 实际新增费用：**7.451754 CNY**，低于10.5 CNY hard cap；
- 所有新请求不包含target GT。

Qwen本身不是更强主分类器，但提供了明显互补信息。T-S有效池上：

| pool | Qwen U0 PA | false-S | S recall | NS recall | NA recall |
|---|---:|---:|---:|---:|---:|
| 052 (n=236) | 73.73% | 4 | 79.68% | 55.56% | 48.39% |
| 053 (n=237) | 78.48% | 4 | 82.81% | **92.86%** | 45.16% |

尤其053的NS recall很高，说明Qwen second opinion确实能补PriorG的NS盲点；但它的类条件可靠性在052/053间变化很大，这也成为zero-label adaptation的新难点。

## 3. Qwen ensemble：有真实增益，但跨域不稳定

简单的source-trained Naive Bayes ensemble把PriorG与Qwen hard decisions联合后，在052→053方向出现明显收益。例如使用PriorG + Qwen U0：

- 053 Frozen PriorG：198/237，PA 83.54%，MCC 0.5596，false-S 8，recall S/NS/NA=88.54/50.00/67.74%；
- zero-label NB ensemble：203/237，PA **85.65%**，MCC **0.5905**，false-S 9，recall=91.15/50.00/67.74%。

也存在更保守的target-unlabeled label-model工作点，例如在053上可达到202/237、MCC 0.5876、false-S 8，且S recall提高而NS/NA不下降。

但在反方向053→052，同类方法没有稳定复现：PriorG+Qwen U0的正确数仍为198/236且MCC下降；更积极的label-model虽然能把PA推到约87.7%，却把NS recall压到0并显著增加false-S。因此这些结果只能视为探索性性能上限，不能作为zero-label部署规则。

## 4. Source-only patient-CV：正式部署检验

为了避免用target GT挑选“看起来好”的配置，055最终要求：超参数和是否启用ensemble必须只由source患者级CV决定，target GT在部署选择后才用于评分。

### Qwen label-model

- source=052 → target=053：source-CV选出的配置在target达到PA 86.08%、MCC 0.5762，但false-S从8增到12，NS recall从50.0%降到28.6%；
- source=053 → target=052：source-CV选出的配置在target反而降到PA 80.51%、MCC 0.5135，明显低于PriorG的83.90% / 0.5946。

因此source-only选参不能可靠判断target上Qwen/DeepSeek互补关系。

### Conservative NB selector

进一步要求候选在source患者CV上至少满足安全条件：PA/MCC不差、false-S不增、三类recall不明显下降；否则自动回退Frozen PriorG。

两个source方向都**没有候选通过安全条件**，所以正式selector在052和053 target上均回退Frozen PriorG。换言之，在不偷看target GT的前提下，当前证据不足以安全启用自动ensemble adaptation。

## 5. 为什么zero-label adaptation现在仍不稳定

055表明问题不再只是`P(Y)`发生变化，而是不同环境中的`P(model outputs | Y)`也会变化。

最直观的例子是Qwen U0的NS recall：052为55.56%，053为92.86%。同一个second-opinion模型在两批材料上的类条件可靠性差异很大。PriorG自身也存在类似但较弱的conditional drift。

因此target无标签系统面对一个不可完全识别的问题：观察到预测分布变化时，它无法可靠区分：
- 真实类别prevalence变了；
- 某个Judge对某一类的敏感性变了；
- 两者同时发生。

BBSE可以解决第一部分，但无法仅凭hard-prediction prevalence可靠恢复第二部分。无标签EM/自训练尝试更新类条件confusion时，又容易由伪标签误差产生自强化。

## 6. 055最终判断

按用户设定的硬目标：

> 新环境 target = 0 labels，系统自动适应，并在PA、MCC、false-S、S/NS/NA recall上取得稳定不错的结果。

**055尚未完全实现。**

已实现的能力：
- zero-label prevalence estimation；
- zero-label shift detection；
- zero-label policy / ensemble adaptation机制；
- Qwen + DeepSeek互补信息可在部分新环境产生真实性能增益。

尚缺少的能力：
- 在target class-conditional model behavior也漂移时，zero-label地判断“哪个Judge此刻更可信”；
- 一个source-only选择规则，能在052↔053和多种shift环境中稳定保持或提升全部主要分类指标。

当前正式部署建议仍是：**Frozen T-S+PriorG作为默认分类器；BBSE做无标签shift monitoring；自动adaptation保持研究状态。** 如果必须完全0标签上线，最安全版本是“检测但不自动改标签”；如果允许极少量target标签，则问题会明显容易很多，但那不属于055目标。

## 7. 费用与执行完整性

- 早期DeepSeek-only / policy / label-model / GMM / robust-policy实验：本地离线；
- Full Qwen extension：429个新调用 + 51个逐条body一致复用；
- 新增Qwen费用：**7.451754 CNY**；
- Qwen runner hard cap：10.5 CNY；
- 无后台进程残留；
- 未使用reserved；
- 未commit/push。
