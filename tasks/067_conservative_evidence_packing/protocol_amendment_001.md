# 067 Execution Accounting Amendment 001

## 背景

067正式stage1（227个GT-blind C48 audit）与stage2（226个changed-pack T-S Judge）完成后，工作目录中另出现一组不同request_id的 stage1v2 / stage2v2 回执：
- stage1v2: 225
- stage2v2: 27

时间上：
- formal stage1: 04:36–04:43 UTC
- formal stage2: 04:48–04:56 UTC
- stage1v2: 04:59–05:04 UTC
- stage2v2: 05:08–05:09 UTC

因此v2发生在正式067预测完成之后，不属于冻结协议的正式stage1/stage2。

## 处理

- 不删除v2回执。
- 不读取/使用其预测结果选择或修改067正式方法。
- 正式性能只由 stage1_jobs.jsonl + stage2_jobs.jsonl 对应的453个request_id决定。
- 正式API费用约 ¥11.839566。
- superseded v2另外252个HTTP200，费用约 ¥8.894004，仅作为执行账记录，不计入正式方法成本。
- 两组request_id无重复；正式结果不依赖v2。

本修订仅修正执行账口径，不修改任何方法、预测或指标。
