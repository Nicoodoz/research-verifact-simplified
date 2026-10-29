# 111 half_extension

111未支持保留update_half：新增1317相对105、107均降低MCC与PA，完整1817的错误放行减少不足以抵消正确S与NA损失。结束109续训＋插值衍生路线。

[最终报告](final_report.md) · [完整指标](final_metrics.md) · [配对数据](comparison.json) · [去正文预测](predictions_sanitized.jsonl) · [费用](cost_status.json) · [自检](final_selfcheck.json)。

旧500与103历史回执复用，新增1317只跑105 label_only、107 label_only、110 update_half；三臂回执齐全。完整1817为原20人的开发选型队列，S1455/NS121/NA241，不是新holdout。

[准备快照](preparation_report.md) · [队列元数据](cohort_metadata.jsonl) · [103原ID](history103_ids.jsonl) · [协议](../../tasks/111_half_extension/protocol.md)。未改旧报告/GT，不自动112；按用户政策未关机，实例继续开机计费。原文、私有回执、凭据、权重和缓存不提交。
