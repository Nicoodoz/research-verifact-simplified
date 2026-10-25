# 064 Amendment 001：Patient-disjoint Future-batch Validation

少量标签只来自calibration patients；选定policy后，应用到sid完全不重叠的future patients。policy库、posterior、风险阈值均与主064相同。

| direction | strategy | budget | oracle match | unsafe | BASE fallback | ΔPA | ΔMCC | ΔNS | ΔNA | labels used | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 052→053 | active_policy | 3 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.0 | False |
| 052→053 | active_policy | 5 | 28.0% | 0.0% | 72.0% | +0.004 | +0.006 | +0.000 | +0.000 | 5.0 | False |
| 052→053 | active_policy | 10 | 4.0% | 0.0% | 96.0% | +0.001 | +0.001 | +0.000 | +0.000 | 10.0 | False |
| 052→053 | active_policy | 20 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 13.6 | False |
| 052→053 | random_global | 3 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.0 | False |
| 052→053 | random_global | 5 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 5.0 | False |
| 052→053 | random_global | 10 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 10.0 | False |
| 052→053 | random_global | 20 | 12.0% | 0.0% | 88.0% | +0.002 | +0.002 | +0.000 | +0.000 | 20.0 | False |
| 053→052 | active_policy | 3 | 92.0% | 8.0% | 92.0% | -0.001 | -0.002 | -0.009 | +0.000 | 3.0 | False |
| 053→052 | active_policy | 5 | 96.0% | 4.0% | 96.0% | -0.000 | -0.001 | -0.003 | +0.000 | 5.0 | False |
| 053→052 | active_policy | 10 | 100.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 9.8 | True |
| 053→052 | active_policy | 20 | 100.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 12.8 | True |
| 053→052 | random_global | 3 | 100.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.0 | True |
| 053→052 | random_global | 5 | 100.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 5.0 | True |
| 053→052 | random_global | 10 | 94.0% | 6.0% | 94.0% | -0.000 | -0.002 | -0.008 | +0.000 | 10.0 | False |
| 053→052 | random_global | 20 | 94.0% | 6.0% | 94.0% | +0.000 | -0.000 | +0.000 | +0.000 | 20.0 | False |

## 结论

**patient-disjoint评估下，0/3/5/10/20 labels仍未在两个方向同时通过。**

这时失败不能再归因于within-batch action region被标注耗尽，需要看是认证样本不足还是source先验/active acquisition仍不合适。

## 边界

- calibration/future按sid完全分离，但仍来自同一development target pool。
- oracle policy沿用完整target GT，仅作诊断。
- 0 API、未使用reserved、未自动commit/push。
