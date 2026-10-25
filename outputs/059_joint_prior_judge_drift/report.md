# 059：Joint Prior and Judge-drift Estimation

## 目标

target无GT时，同时估类别比例与每个Judge的两个全局log-odds漂移参数：S偏移、NS相对NA偏移。

prior由联合DeepSeek+Qwen 4维log-odds协方差估计；全局additive bias不改变协方差。随后用target均值减去source类条件均值按估计prior的混合值得到theta。

## 真实052↔053无标签估计

| source→target | pi_hat(S/NS/NA) | DS θS | DS θNS | Q θS | Q θNS |
|---|---|---:|---:|---:|---:|
| 052→053 | 0.890/0.000/0.110 | -0.433 | -0.045 | -0.066 | +0.135 |
| 053→052 | 0.740/0.070/0.190 | +0.265 | +0.037 | -0.084 | -0.158 |

上述结果在GT评价前先写入actual_unlabeled.csv并记录哈希。

## 解盲评价

| source→target | prior L1 | theta MAE vs oracle | R2 joint | R2 DS | R2 Qwen |
|---|---:|---:|---:|---:|---:|
| 052→053 | 0.160 | 0.279 | 0.170 | 0.024 | 0.211 |
| 053→052 | 0.117 | 0.219 | 0.174 | 0.033 | 0.207 |

## Synthetic recovery（n=960汇总）

- prior L1 mean: **0.074**
- theta MAE mean: **0.085**
- 非零drift sign accuracy: **99.656%**
- 事前synthetic门槛：**PASS**

## 结论

**059在合成已知漂移上可恢复，但真实common-shift假设不足。**

说明估计器本身可工作，但真实Judge变化不是简单的每个Judge两个全局bias；不应直接把这4个参数送入060。

## 边界

- theta描述score-space全局bias，不是完整confusion matrix或class-specific recall。
- 052/053为development内部batch。
- 0 API、未使用reserved、未自动commit/push。

## 为什么真实common-shift失败

052→053解盲后的class-specific均值漂移并不是统一平移：

- DeepSeek θS：真S约 -0.108、真NS +0.229、真NA +0.982；
- DeepSeek θNS：真S约 -0.117、真NS +0.846、真NA +0.799；
- Qwen θS：真S约 +0.293、真NS +1.968、真NA +0.487；
- Qwen θNS：真S约 -0.020、真NS **+3.299**、真NA -0.012。

因此最明显的变化是**类特异性的**，尤其Qwen对真NS的score geometry发生大幅变化，而不是“Qwen整体更偏NS”这么简单。这与055中Qwen NS recall跨052/053大幅变化一致。

同时，059的covariance-only联合prior估计在真实两方向L1为0.160/0.117，明显不如054的DeepSeek-BBSE真实batch估计（约0.0228/0.0312）。因此059不替代BBSE prevalence sensor；其价值是证明“简单global drift参数化”不足，并定位需要class-dependent reliability drift。
