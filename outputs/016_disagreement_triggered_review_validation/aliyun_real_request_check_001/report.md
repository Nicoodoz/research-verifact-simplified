# 阿里云真实实验请求测试

- 范围：016原冻结队列第一条从未发送的Qwen请求，只改阿里云模型标识，原claim、C48、prompt和生成参数不变。
- HTTP状态：200；耗时：11.88秒；有效结构化预测：True。
- 本次usage估算／预留：¥0.01749600；016累计：¥11.82850223/¥40（非账单，旧未知预留保持）。
- 请求、回执、usage及完整回答分别保存在source_job.json、job.json、attempt_001/和normalized_response.json；密钥不落盘。
- 没有GT效果评价、批量续跑或分歧复核。成功回答单独保留，未来登记供应商切换时应复用，不得再生成；单次成功不能证明批量稳定或跨供应商结果等价。
- [发送前登记](authorization.json) · [结果汇总](summary.json)。计价依据：[阿里云北京模型价格](https://help.aliyun.com/zh/model-studio/qwen3-8-27b)。
