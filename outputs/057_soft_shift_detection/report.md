# 057：Soft Multi-view Conditional-shift Detection

## 核心问题

056的hard-label联合残差没过门槛。057固定使用DeepSeek T-S + Qwen完整6维scores，检验连续soft信息是否能恢复conditional-shift信号。

主方法：source-only标准化 + 固定128维RBF Random Fourier Features；BBSE仍只估target prevalence；soft residual比较target mean embedding与source类条件embedding按BBSE prior重混合后的差异。

## 真实052↔053无标签结果

| source→target | view | residual | H0 q95 | p | alarm |
|---|---|---:|---:|---:|---|
| 052→053 | joint | 0.0302 | 0.0420 | 0.2324 | False |
| 052→053 | ds | 0.0165 | 0.0339 | 0.3733 | False |
| 052→053 | qwen | 0.0255 | 0.0407 | 0.2749 | False |
| 053→052 | joint | 0.0370 | 0.0510 | 0.2379 | False |
| 053→052 | ds | 0.0131 | 0.0289 | 0.4033 | False |
| 053→052 | qwen | 0.0304 | 0.0541 | 0.3153 | False |

actual_unlabeled.csv在GT评价前先写入并记录SHA256；上述alarm不读取target GT。

## 解盲后与055实际adaptation关联

| source→target | BBSE L1 | joint alarm | 055 ΔPA | ΔMCC | Δfalse-S | ΔNS recall |
|---|---:|---|---:|---:|---:|---:|
| 052→053 | 0.023 | False | +0.025 | +0.017 | +4 | -0.214 |
| 053→052 | 0.031 | False | -0.034 | -0.081 | +2 | -0.056 |

## 与056 hard detector同门槛比较

| source | soft H0 FPR | soft H1 detection | hard056 H1 detection | soft增量 | 事前门槛 |
|---|---:|---:|---:|---:|---|
| 052 | 0.046 | 0.644 | 0.552 | +0.093 | FAIL |
| 053 | 0.049 | 0.566 | 0.382 | +0.184 | FAIL |

## 结论

**057机制screen未通过。**

在固定soft detector下，连续DeepSeek+Qwen scores仍不足以稳定识别conditional behavior replacement。按事前边界不继续调RFF维度、bandwidth或transform。

## 边界

- 057检验的是shift diagnosis，不修改任何final label。
- 052/053仍是development内部claim批次，不是外部domain。
- H1 conditional replacement是压力测试，不代表所有真实漂移形态。
- 0 API、未使用reserved、未自动commit/push。
