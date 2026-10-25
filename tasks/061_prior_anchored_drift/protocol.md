# 061：Prior-Anchored Class-specific Drift Estimation

## 目标

060同时自由估target prior与12维class-specific Judge drift，出现明显不可识别性。061只验证一个问题：

> 如果把target prior固定，060的class-specific drift还能不能恢复？

不修改060的score表示、source Gaussian锚点、covariance shrinkage、tau=20、delta clip、EM收敛规则；唯一变化是prior不再参与M-step更新。

## 三个对照

1. **Oracle-fixed prior**：固定真实target prior，只作诊断上限。
2. **BBSE-fixed prior**：只用source有标签Frozen PriorG confusion + target无标签Frozen PriorG hard predictions估prior，再固定该prior；这是0标签可部署版本。
3. **060 joint-free prior**：历史基线，不重选参数。

## Fixed-prior EM

E-step仍根据固定pi与当前class-specific delta计算latent class responsibilities。

M-step只更新12维delta：
- 每类raw shift由responsibility加权target mean得到；
- 与060完全相同，向shared global shift做tau=20 hierarchical shrinkage；
- shared shift不向0收缩；
- source-z空间delta clip固定[-3,3]。

固定两个deterministic starts：
- delta=0；
- 将target总体均值减去固定prior下source混合均值得到shared shift，并复制到三个class。

选择penalized likelihood更高者。

## BBSE sensor

Frozen monitor沿用054：
- DeepSeek T-S scores；
- 冻结G与reference prior correction；
- source GT confusion matrix；
- target只看Frozen PriorG hard predictions；
- constrained simplex least squares估target prior。

Synthetic中若注入DeepSeek log-odds drift，同样作用于Frozen monitor的DeepSeek相对logits，因此BBSE会真实暴露“Judge漂移污染prior sensor”的问题。

## Synthetic

完全沿用060：
- source=052/053；
- prior=source、60/20/20、60/30/10、60/10/30；
- n=240/480/960；
- 6种class-specific drift pattern；
- 每条件30次。

同时评价Oracle-fixed与BBSE-fixed：
- prior L1（BBSE）；
- 12维delta MAE；
- 非零drift sign accuracy。

## 真实052↔053

先生成BBSE-fixed的无标签结果并冻结；Oracle结果明确标记为GT知情诊断。

评价：
- fixed prior L1；
- true class-specific delta MAE；
- weighted class-specific R2；
- |true delta|>=0.5 的sign accuracy；
- 与060 joint-free R2固定比较。

## 事前判读

A. 若Oracle-fixed满足：
- n=960 delta MAE <=0.30；
- n=960 sign accuracy >=90%；
- 真实两方向R2均 >=0.50；

则证明060主要败在prior-drift confounding，而不是class-specific drift表示本身。

B. 若Oracle通过且BBSE-fixed同时满足：
- n=960 prior L1 <=0.10；
- n=960 delta MAE <=0.35；
- n=960 sign accuracy >=90%；
- 真实两方向prior L1 <=0.15且R2 >=0.50；

则当前zero-label分解可进入动态decision。

C. 若Oracle通过、BBSE失败：下一瓶颈是prior sensor在Judge drift下被污染。
D. 若Oracle本身失败：12维class-specific Gaussian-shift表示/估计仍不足，应转低秩或其他结构化漂移。

## 边界

- Oracle prior不是部署方法。
- 052/053仍是development内部batch。
- 0 API，不使用reserved，不自动commit/push。
