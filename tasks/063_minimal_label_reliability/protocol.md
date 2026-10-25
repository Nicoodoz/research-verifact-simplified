# 063：Minimal-label Target Reliability Calibration

## 目标

062之后已知：
- target类别比例可由BBSE稳定估计；
- zero-label能检测明显Judge drift，但NS/NA少数类conditional reliability难以恢复；
- 继续增加zero-label drift自由度并不能补齐链路。

063直接回答：

> 在新环境给多少个target真标签，能够把Judge reliability校准到足以安全改善最终判定？

本任务不调用新模型API，只复用055已有DeepSeek/Qwen scores与GT，模拟few-label部署。
## 固定输入与Judge

只使用两个真正不同的Judge视图：
1. DeepSeek Frozen T-S + PriorG hard prediction；
2. Qwen U0 hard prediction。

每条claim形成joint pattern：
pattern = 3 * DeepSeek_label + Qwen_label，共9种。

不使用T-S/U2/PriorG等多个高度相关DeepSeek变体作为独立Judge，避免条件独立假设伪增信息。

target prior仍由Frozen PriorG + BBSE无标签估计，不因few-label calibration重新学习。
## Reliability calibration model

source有GT，先估每个真实类别下的joint-pattern分布：
P_s(pattern | Y=y)。

source 3×9 pattern counts固定使用Jeffreys +0.5平滑，避免稀疏pattern出现严格0概率。

target给出b个真标签后，统计：
N_t(y, pattern)。

使用source作为Dirichlet shrinkage prior：
alpha(y,p) = kappa * P_s(p | y) + N_t(y,p)。

得到target reliability：
P_hat_t(pattern | Y=y) = alpha(y,p) / sum_p alpha(y,p)。

最终对未标注claim：
P(Y=y | pattern) ∝ BBSE_pi_t(y) * P_hat_t(pattern | Y=y)。

这是063唯一主校准器；不训练新的黑盒分类器。
## kappa选择

不看未标注评估GT。

候选：
kappa ∈ {1, 3, 10, 30, 100}。

若budget=0，使用source reliability，不做target calibration。

若budget>0：
- 只在已获得的target labeled subset内部做leave-one-out；
- 对每个kappa，逐个移除一个label，用剩余few labels校准；
- 计算被移除label的负log predictive probability；
- 选择平均NLL最低kappa；
- 再用全部few labels拟合最终target reliability。

tie按更大kappa优先，避免小样本过拟合。
## Label budget

固定：
b ∈ {0, 5, 10, 20, 40}。

每个budget的已标注claims从最终评估集中移除。
主指标只在**剩余未标注claims**上计算，避免把人工已知GT直接算成正确导致虚假提升。

同时记录operation-level secondary metrics：
若人工已标注claims直接采用GT，整个batch的最终系统表现可达到什么水平。
## 三种采样策略

### 1. random
patient-diverse随机抽样：
- 固定seed；
- 尽量先覆盖不同sid，再在同一sid取第二条；
- 重复50次。

### 2. active（部署主方案）
完全不看target GT。

根据source reliability + BBSE prior，计算每个joint pattern的posterior entropy：
H(Y | pattern)。

贪心选择：
score(pattern) = H / (1 + 当前已选该pattern数量)。

优先未被选过的sid；如果所有剩余候选都来自已覆盖sid，再允许重复患者。
同分用固定seed hash打散。
重复50个固定seed，衡量tie/患者分布敏感性。

### 3. oracle-balanced（仅诊断）
使用target GT，尽量均匀抽S/NS/NA并保持patient diversity。
这是few-label信息上限，不是部署方法。
重复50次。
## 评价

两个真实方向：
- source052 → target053；
- source053 → target052。

每个strategy × budget × repeat：
1. 选few-label subset；
2. 用source + labeled subset估target reliability；
3. 在剩余未标注claims上预测；
4. 同一holdout上计算Frozen PriorG baseline。

指标：
- PA；
- MCC；
- false-S rate = false-S / target non-S；
- S recall；
- NS recall；
- NA recall；
- 相对Frozen PriorG的delta；
- few-label subset中S/NS/NA数量；
- 选定kappa。

另外记录safe-win：
- PA >= baseline；
- MCC >= baseline；
- false-S rate <= baseline；
- NS recall >= baseline；
- NA recall >= baseline - 0.02；
- 且PA或MCC至少一个严格提升。
## “很好解决”的事前标准

对可部署active策略，某个最小budget b只有同时满足才算补齐missing reliability link：

两个source→target方向都满足：
1. mean ΔPA >= 0；
2. mean ΔMCC >= +0.02；
3. mean Δfalse-S-rate <= 0；
4. mean ΔNS recall >= 0；
5. mean ΔNA recall >= -0.02；
6. safe-win rate >= 70%。

若active没有budget通过：
- oracle-balanced若通过，说明主要瓶颈是active acquisition没有稳定抓到少数类；
- oracle-balanced也不通过，说明当前joint-pattern reliability calibrator本身不够。

random用于回答“不做主动选样需要多少标签”。
## 额外诊断

- 报告每个budget平均实际获得多少S/NS/NA标签；
- 特别关注“至少获得1个NS / 2个NS / 1个NA”时的条件表现；
- 报告budget增加后的边际收益；
- budget=40若仍未达到active标准，不在本任务内继续追加80或调safe-win门槛。

## 边界

- 052/053仍是development内部池，不是外部医院。
- 这是“给少量target人工标签”的模拟实验，不等于实际标注成本已验证。
- 标签采样与calibration规则在正式结果前冻结。
- 0 API，不使用reserved，不自动commit/push。
