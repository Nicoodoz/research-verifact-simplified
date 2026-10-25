# 064 Amendment 002：Future-policy Exposure Fix

少量标签只来自calibration patients；选定policy后，应用到sid完全不重叠的future patients。policy库、posterior、风险阈值均与主064相同。

| direction | strategy | budget | oracle match | unsafe | BASE fallback | ΔPA | ΔMCC | ΔNS | ΔNA | labels used | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 052→053 | active_policy | 3 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.0 | False |
| 052→053 | active_policy | 5 | 48.0% | 0.0% | 52.0% | +0.008 | +0.009 | +0.000 | +0.000 | 5.0 | False |
| 052→053 | active_policy | 10 | 58.0% | 0.0% | 42.0% | +0.011 | +0.013 | +0.000 | +0.000 | 10.0 | False |
| 052→053 | active_policy | 20 | 58.0% | 0.0% | 42.0% | +0.011 | +0.013 | +0.000 | +0.000 | 13.9 | False |
| 052→053 | random_global | 3 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.0 | False |
| 052→053 | random_global | 5 | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 5.0 | False |
| 052→053 | random_global | 10 | 4.0% | 0.0% | 96.0% | +0.000 | +0.001 | +0.000 | +0.000 | 10.0 | False |
| 052→053 | random_global | 20 | 10.0% | 0.0% | 90.0% | +0.001 | +0.001 | +0.000 | +0.000 | 20.0 | False |
| 053→052 | active_policy | 3 | 72.0% | 28.0% | 72.0% | -0.002 | -0.007 | -0.020 | +0.000 | 3.0 | False |
| 053→052 | active_policy | 5 | 90.0% | 10.0% | 90.0% | -0.001 | -0.004 | -0.012 | +0.000 | 5.0 | False |
| 053→052 | active_policy | 10 | 88.0% | 12.0% | 88.0% | -0.001 | -0.005 | -0.015 | +0.000 | 9.9 | False |
| 053→052 | active_policy | 20 | 90.0% | 10.0% | 90.0% | -0.001 | -0.004 | -0.012 | +0.000 | 12.9 | False |
| 053→052 | random_global | 3 | 98.0% | 2.0% | 98.0% | -0.000 | -0.001 | -0.003 | +0.000 | 3.0 | False |
| 053→052 | random_global | 5 | 98.0% | 2.0% | 98.0% | +0.000 | -0.000 | +0.000 | +0.000 | 5.0 | False |
| 053→052 | random_global | 10 | 98.0% | 2.0% | 98.0% | -0.000 | -0.001 | -0.003 | +0.000 | 10.0 | False |
| 053→052 | random_global | 20 | 100.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 20.0 | True |

## 结论

**patient-disjoint评估下，0/3/5/10/20 labels仍未在两个方向同时通过。**

这时失败不能再归因于within-batch action region被标注耗尽，需要看是认证样本不足还是source先验/active acquisition仍不合适。

## 边界

- calibration/future按sid完全分离，但仍来自同一development target pool。
- oracle policy沿用完整target GT，仅作诊断。
- 0 API、未使用reserved、未自动commit/push。
