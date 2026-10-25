# 062：Low-rank Empirical Transport for Zero-label Judge Drift

## 方法

BBSE只负责target类别比例；Judge drift不再用Gaussian latent mixture，而是直接平移source三类经验score分布并用RFF/MMD匹配target无标签分布。主模型为rank-1：delta_y=a_y v；rank-2仅作诊断。

所有actual GT-blind结果先写入actual_unlabeled.csv并冻结SHA256，之后才解盲评价。

## Synthetic rank-1 screen（n=960）

- none false-accept: **0.0%**
- rank-1真值pattern accept: **58.8%**
- active-coordinate delta MAE: **0.607**
- inactive spurious MAE: **0.110**
- sign accuracy: **55.0%**
- 事前synthetic门槛：**FAIL**

## 真实052↔053

| direction | rank | accept | gain / q95 | BBSE L1 | R2 | MAE | sign | true rank1/rank2 energy | 061 Gaussian R2 |
|---|---:|---|---|---:|---:|---:|---:|---|---:|
| 052→053 | 1 | False | -0.0090 / 0.0007 | 0.023 | 0.000 | 0.763 | 0.000 | 0.902/0.995 | 0.300 |
| 052→053 | 2 | False | -0.0128 / -0.0077 | 0.023 | 0.000 | 0.763 | 0.000 | 0.902/0.995 | 0.300 |
| 053→052 | 1 | False | -0.0043 / 0.0009 | 0.031 | 0.000 | 0.763 | 0.000 | 0.902/0.995 | 0.066 |
| 053→052 | 2 | False | -0.0053 / -0.0011 | 0.031 | 0.000 | 0.763 | 0.000 | 0.902/0.995 | 0.066 |

## Rank-2 mixed diagnostic

- mixed accept mean: **100.0%**
- mixed delta MAE mean: **0.614**
- mixed delta R2 mean: **-0.936**

## 结论

**rank-1 empirical transport连source-controlled synthetic门槛都未通过。**

说明低秩经验平移本身仍不能稳定解决伪漂移/恢复问题，不应仅凭真实development fit继续堆同类参数。

## 边界

- low-rank结构来自development GT诊断启发，真实052/053结果不是独立外部验证。
- rank-2仅为诊断上限。
- 0 API、未使用reserved、未自动commit/push。

## Pattern-level diagnosis

n=960 rank-1 synthetic按真实漂移类型拆分：
- S_QS_down：accept 82.5%，active MAE 0.135，sign 82.5%；
- NS_QNS：accept 67.5%，active MAE 0.680，sign 65.0%；
- NS_DSNS：accept 45.0%，active MAE 0.685，sign 45.0%；
- NA_DSS：accept 40.0%，active MAE 0.928，sign 27.5%。

因此062并不是“完全看不到低秩漂移”：占比最大的Supported类发生简单漂移时可以较好恢复；真正失败集中在NS/NA少数类。结合060/061，这说明当前zero-label混合分布对少数类class-specific reliability change的信息仍不足。

另一个重要结论是：真实052↔053的class-mean shift矩阵在GT下确实高度低秩（rank-1 90.24%，rank-2 99.46%），但这并不意味着真实条件分布可以通过“每类整体平移”从source transport到target。真实两方向rank-1/rank-2 heldout gain均为负，说明该transport在未见target half上反而比no-shift更差。
