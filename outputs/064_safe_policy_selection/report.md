# 064：Target-local Safe Policy Selection

## 核心变化

不再重建target分类器。只在Frozen PriorG附近认证局部Veto/Rescue policy；证据不足时回退BASE。source只提供每个policy-signature的弱先验（等效1个target label）。

## GT-blind结构

| direction | disagreement claims | zero-label selected | policy changes |
|---|---:|---|---|
| 052→053 | 27 | BASE | {"BASE": 0, "C60": 27, "C80": 21, "R90": 6, "V60": 21, "V80": 15} |
| 053→052 | 26 | BASE | {"BASE": 0, "C60": 26, "C80": 25, "R90": 3, "V60": 23, "V80": 22} |

## Oracle-safe policy（仅诊断）

| direction | oracle | safe nonBASE policies |
|---|---|---|
| 052→053 | R90 | R90 |
| 053→052 | BASE | None |

## Few-label结果

| direction | strategy | budget | oracle match | safe switch | unsafe switch | BASE fallback | ΔPA | ΔMCC | ΔNS | ΔNA | labels S/NS/NA | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 052→053 | active_policy | 3 | 0.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 2.1/0.1/0.8 | False |
| 052→053 | active_policy | 5 | 46.0% | 46.0% | 0.0% | 54.0% | +0.005 | +0.006 | +0.000 | +0.000 | 4.0/0.1/1.0 | False |
| 052→053 | active_policy | 10 | 18.0% | 18.0% | 0.0% | 82.0% | +0.001 | +0.000 | +0.000 | +0.000 | 7.9/0.2/2.0 | False |
| 052→053 | active_policy | 20 | 0.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 15.1/0.9/4.0 | False |
| 052→053 | random_global | 3 | 0.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 2.4/0.3/0.3 | False |
| 052→053 | random_global | 5 | 0.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 4.0/0.3/0.7 | False |
| 052→053 | random_global | 10 | 0.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 8.0/0.7/1.3 | False |
| 052→053 | random_global | 20 | 2.0% | 2.0% | 0.0% | 98.0% | +0.000 | +0.000 | +0.000 | +0.000 | 15.9/1.2/2.9 | False |
| 053→052 | active_policy | 3 | 70.0% | 0.0% | 30.0% | 70.0% | -0.001 | -0.006 | -0.017 | +0.000 | 2.1/0.5/0.4 | False |
| 053→052 | active_policy | 5 | 100.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 3.2/0.8/1.0 | True |
| 053→052 | active_policy | 10 | 96.0% | 0.0% | 4.0% | 96.0% | -0.000 | -0.001 | -0.003 | +0.000 | 7.5/1.4/1.2 | False |
| 053→052 | active_policy | 20 | 100.0% | 0.0% | 0.0% | 100.0% | +0.000 | +0.000 | +0.000 | +0.000 | 15.9/2.7/1.4 | True |
| 053→052 | random_global | 3 | 98.0% | 0.0% | 2.0% | 98.0% | -0.000 | -0.000 | -0.001 | +0.000 | 2.4/0.2/0.3 | False |
| 053→052 | random_global | 5 | 98.0% | 0.0% | 2.0% | 98.0% | +0.000 | -0.000 | -0.001 | +0.000 | 4.3/0.3/0.4 | False |
| 053→052 | random_global | 10 | 98.0% | 0.0% | 2.0% | 98.0% | -0.000 | -0.000 | -0.001 | +0.000 | 7.8/0.8/1.4 | False |
| 053→052 | random_global | 20 | 92.0% | 0.0% | 8.0% | 92.0% | -0.000 | -0.002 | -0.005 | +0.000 | 16.1/1.4/2.5 | False |

## 结论

**0/3/5/10/20个target标签下，active_policy仍未在两个方向同时闭合链路。**

这说明即使把问题降成局部policy认证，当前policy库/认证规则仍不足；应结合oracle-safe结构判断是policy覆盖不足还是认证过于保守。

## 边界

- policy library受既有development分析启发，真实052/053不是独立外部验证。
- rescue允许posterior mean false-rescue rate最多25%，而不是要求global false-S绝对不增加。
- oracle仅定义当前环境正确的切换/回退，不参与few-label选择。
- 0 API、未使用reserved、未自动commit/push。
