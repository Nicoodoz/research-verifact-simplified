# 后续API与单A800最小一致性检查（方案，未执行）

建议主模型qwen3.5-35b-a3b，必要备选qwen3.5-27b。固定ID见future_A800_bridge24.jsonl，24例S/NS/NA各8，选择发生在099质量结果之前，不能换成API/本地更易一致的病例。

1. 用户确认A80080GB实例后，独立新环境固定引擎/torch/CUDA/transformers版本。下载官方checkpoint的精确revision（本轮qwen3.5-35b-a3b为59d61f3ce65a6d9863b86d2e96597125219dc754），记录所有权重、tokenizer和chat_template SHA；BF16、TP1、单并发、text-only，不启用量化、投机或MTP，不改旧085/096环境。按24条实际token长度+完整输出余量选max_model_len，不截断或重选长例；无法容纳时先报告该配置的真实部署限制。

2. 从099私有原始job复制完全相同system/user文字，原O/claim SHA逐例核对，GT不进请求。temperature0、top_p1、thinking开启。阿里云thinking_budget2048对应vLLM新版本的thinking_token_budget2048，并启用正确reasoning parser/起止token；不能把参数原样照搬而假定已生效。3.8的low力度/模板设置也需核对。参考[官方thinking budget控制](https://docs.vllm.ai/en/stable/features/reasoning_outputs/)。本地max_tokens通常包含思考，需为2048思考+512回答留足总上限；若无法单独约束最终512，必须标明差异并检查上限是否实际触发，不能声称参数完全等价。记录强制结束思考的token序列；平台内部强制策略未知。

3. 先做2条固定技术检查（计入24），再一次运行其余22。复用099对应API首次答案；如需排除时段漂移，另行授权8条固定hash的同body API桥接，估算按本轮主模型实际token费用×8并预留最大输出，不继承099剩余额度。本地在固定8条上重复一次，比较引擎自身波动，不择优。保存完整生成参数、token计数、结束原因、输入SHA和回执。

4. 主要看24条raw标签一致数/百分比、API→本地三分类转移、invalid、false-S与PA/MCC变化、显存峰值/首token和总时延；同时报告严格及同一外层围栏规范化解析。24条平衡面板不能当自然性能估计。初步工程门槛可设全部有效且至少23/24标签一致；≥2个分歧或任何系统性类别偏移时先定位权重/模板/预算/算子问题，不直接扩大。即使23/24也只是小样本可行性，不是统计等效或跨医院泛化证据。

5. API精确权重revision/精度始终无凭据时保留unknown。BF16仍明显不一致，则如实将API与本地当两个后端，后续同模型公平比较在同一后端内完成，不通过改prompt、选病例或多次重发制造一致。全流程不改变099选型主表与098冻结材料。
