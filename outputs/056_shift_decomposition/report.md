# 056：Unlabeled Shift Decomposition

## 核心问题

target完全无GT时，能否先用BBSE估prevalence，再用DeepSeek×Qwen联合输出判断当前变化是否仍符合纯label shift。

主残差：TV(observed target joint outputs, source P(D,Q|Y) × BBSE pi_hat)。阈值来自source纯label-shift重采样95%分位。

## 真实052↔053无标签诊断

| source→target | DS-BBSE pi(S/NS/NA) | DS-Qwen prior L1差 | joint TV | H0 q95 | p | alarm |
|---|---|---:|---:|---:|---:|---|
| 052→053 | 0.816/0.064/0.119 | 0.223 | 0.040 | 0.064 | 0.3503 | False |
| 053→052 | 0.785/0.068/0.147 | 0.122 | 0.039 | 0.070 | 0.4363 | False |

上述alarm计算不读取target GT；actual_unlabeled.csv先写入并记录哈希，随后才生成下面的GT评价。

## 解盲后评价与055关联

| source→target | true pi | DS-BBSE L1 | Qwen-BBSE L1 | 055 label-model ΔPA | ΔMCC | Δfalse-S | ΔNS recall | alarm |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 052→053 | 0.810/0.059/0.131 | 0.023 | 0.246 | +0.025 | +0.017 | +4 | -0.214 | False |
| 053→052 | 0.792/0.076/0.131 | 0.031 | 0.153 | -0.034 | -0.081 | +2 | -0.056 | False |

## 纯label shift vs conditional replacement压力测试

| source | n=240平均H0 false-alarm | n=240平均H1 detection | 事前门槛 |
|---|---:|---:|---|
| 052 | 0.041 | 0.552 | FAIL |
| 053 | 0.057 | 0.382 | FAIL |

H0只改变类别比例并保持source类条件Judge行为；H1保持同一类别比例，但把类条件DeepSeek×Qwen行为替换为另一批真实观测行为。

## 结论

**056机制screen未通过。** 当前DeepSeek+Qwen无标签联合输出不足以稳定区分纯label shift与conditional behavior replacement。

按事前边界不应继续调同一detector；优先考虑few-label target reliability calibration，而不是继续堆zero-label动态机制。

## 边界

- 052/053都是development内部claim批次，不是外部医院或新数据集。
- H1是利用另一批真实P(D,Q|Y)做conditional replacement的压力测试，不等于真实部署漂移的完整生成过程。
- 056只做shift diagnosis，不修改final label，不宣称解决zero-label adaptation。
- 0 API、未使用reserved、未自动commit/push。
