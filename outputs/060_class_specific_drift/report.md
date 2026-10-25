# 060：Unlabeled Class-specific Judge-drift Estimation

## 核心问题

059的真实Judge漂移明显依赖真实类别。060用source anchored latent mixture，在target 0标签下同时估target prior和3×4 class-specific score drift。

## 真实052↔053无标签估计

| source→target | pi_hat(S/NS/NA) | effective mass(S/NS/NA) | iterations |
|---|---|---|---:|
| 052→053 | 0.861/0.000/0.139 | 204.1/0.0/32.9 | 15 |
| 053→052 | 0.683/0.157/0.159 | 161.3/37.1/37.6 | 19 |

actual_unlabeled.csv先写入并记录哈希，随后才进行target GT评价。

## 解盲评价

| source→target | prior L1 | delta MAE | class-specific R2 | 059 global R2 | sign acc |
|---|---:|---:|---:|---:|---:|
| 052→053 | 0.118 | 0.792 | 0.004 | 0.170 | 0.600 |
| 053→052 | 0.218 | 0.859 | -0.254 | 0.174 | 0.600 |

## Synthetic recovery（n=960）

- prior L1 mean: **0.204**
- class-specific delta MAE mean: **0.573**
- nonzero drift sign accuracy: **93.32%**
- synthetic门槛：**FAIL**

## 结论

**060 synthetic recovery未过门槛。**

当前12维class-specific latent mixture本身还不够稳定，不进入动态决策。

## 边界

- 估计的是score-space class-specific drift，不是完整target confusion matrix。
- 052/053仍是development内部batch。
- 0 API、未使用reserved、未自动commit/push。

## 失败机制

060的主要失败不是“看不出漂移方向”，而是 **target prior 与 class-specific drift不可稳定分离**。

最明显的真实例子是052→053：
- true NS prevalence约5.9%；
- 无标签EM把NS effective mass估到接近0；
- 于是本应由“真NS类的Qwen/DeepSeek行为变化”解释的target样本，被S/NA component与其delta吸收。

这说明当少数类比例低、source少数类样本也少时，允许每个latent class自由移动4维均值，会出现多组近似解释：
- “NS仍存在，但NS Judge行为大幅漂移”；
- “NS比例变少，S/NA component移动来解释这些点”。

仅靠当前DeepSeek+Qwen 4维无标签scores无法稳定区分这些解释。

因此下一步若继续zero-label，应优先尝试**结构化/低秩class-specific drift**，例如只允许少数预定义的类别×Judge交互方向，而不是完整12维自由delta。
