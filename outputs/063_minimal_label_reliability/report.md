# 063：Minimal-label Target Reliability Calibration

## 方法

固定BBSE target prior；只用Frozen PriorG与Qwen U0两个Judge的9种joint pattern。source给出P(pattern|Y)作为Dirichlet prior，few target labels更新target reliability；kappa仅在few-label subset内部LOO选择。

主评估在未标注holdout claims上，与同一holdout的Frozen PriorG比较。

## 预算结果

| direction | strategy | budget | ΔPA | ΔMCC | Δfalse-S rate | ΔNS | ΔNA | safe-win | labels S/NS/NA | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 052→053 | active | 5 | +0.012 | -0.058 | +0.255 | -0.338 | -0.110 | 0.0% | 2.6/0.5/1.9 | False |
| 052→053 | active | 10 | +0.013 | -0.057 | +0.260 | -0.488 | -0.048 | 0.0% | 4.9/1.2/3.9 | False |
| 052→053 | active | 20 | +0.008 | -0.068 | +0.269 | -0.496 | -0.035 | 0.0% | 9.4/2.4/8.3 | False |
| 052→053 | active | 40 | +0.012 | -0.044 | +0.234 | -0.467 | +0.000 | 0.0% | 18.9/5.0/16.1 | False |
| 052→053 | oracle_balanced | 5 | +0.015 | -0.018 | +0.158 | -0.258 | -0.055 | 14.0% | 2.0/2.0/1.0 | False |
| 052→053 | oracle_balanced | 10 | +0.021 | -0.011 | +0.164 | -0.276 | -0.058 | 0.0% | 4.0/3.0/3.0 | False |
| 052→053 | oracle_balanced | 20 | +0.017 | -0.022 | +0.149 | -0.309 | -0.061 | 0.0% | 7.0/7.0/6.0 | False |
| 052→053 | oracle_balanced | 40 | +0.027 | -0.004 | +0.186 | -0.500 | -0.063 | 0.0% | 14.0/13.0/13.0 | False |
| 052→053 | random | 5 | +0.007 | -0.015 | +0.095 | -0.194 | +0.004 | 34.0% | 4.0/0.2/0.8 | False |
| 052→053 | random | 10 | +0.006 | -0.036 | +0.164 | -0.332 | -0.017 | 2.0% | 7.9/0.5/1.6 | False |
| 052→053 | random | 20 | +0.017 | -0.037 | +0.220 | -0.398 | -0.028 | 2.0% | 15.8/1.5/2.7 | False |
| 052→053 | random | 40 | +0.024 | -0.038 | +0.260 | -0.458 | -0.035 | 0.0% | 32.0/2.6/5.4 | False |
| 053→052 | active | 5 | +0.006 | -0.040 | +0.171 | -0.320 | -0.059 | 0.0% | 2.0/1.2/1.7 | False |
| 053→052 | active | 10 | +0.032 | +0.015 | +0.211 | -0.355 | -0.014 | 0.0% | 3.8/2.3/3.8 | False |
| 053→052 | active | 20 | +0.015 | -0.045 | +0.282 | -0.349 | -0.135 | 0.0% | 8.7/4.1/7.2 | False |
| 053→052 | active | 40 | +0.022 | +0.024 | +0.161 | -0.294 | +0.000 | 0.0% | 17.7/8.2/14.1 | False |
| 053→052 | oracle_balanced | 5 | +0.014 | -0.018 | +0.167 | -0.318 | -0.030 | 0.0% | 2.0/2.0/1.0 | False |
| 053→052 | oracle_balanced | 10 | +0.021 | -0.006 | +0.176 | -0.353 | -0.019 | 0.0% | 4.0/3.0/3.0 | False |
| 053→052 | oracle_balanced | 20 | +0.013 | -0.019 | +0.171 | -0.405 | -0.026 | 0.0% | 7.0/7.0/6.0 | False |
| 053→052 | oracle_balanced | 40 | +0.043 | +0.049 | +0.164 | -0.384 | -0.021 | 4.0% | 14.0/13.0/13.0 | False |
| 053→052 | random | 5 | +0.005 | -0.015 | +0.120 | -0.282 | +0.008 | 0.0% | 4.0/0.4/0.6 | False |
| 053→052 | random | 10 | +0.020 | +0.005 | +0.146 | -0.325 | +0.019 | 0.0% | 7.8/0.9/1.3 | False |
| 053→052 | random | 20 | +0.028 | +0.013 | +0.170 | -0.352 | +0.023 | 0.0% | 15.8/1.7/2.5 | False |
| 053→052 | random | 40 | +0.029 | +0.007 | +0.188 | -0.364 | -0.012 | 0.0% | 31.9/3.2/4.9 | False |

## 最小通过budget

- random: **None**
- active: **None**
- oracle-balanced（诊断）: **None**

## 结论

**到40个target labels，oracle-balanced也没有让当前joint-pattern reliability calibrator两方向同时通过。**

因此不能说missing link已补齐；需要比9-pattern reliability table更有表达力的few-label calibrator。

## 边界

- oracle-balanced知道target GT，仅作信息上限。
- 052/053仍是development内部池。
- 0 API、未使用reserved、未自动commit/push。
