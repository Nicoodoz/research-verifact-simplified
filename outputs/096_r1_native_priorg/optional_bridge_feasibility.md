# 可选Original-style@V4：尚未接入，不冒充已运行

本轮只做离线可行性盘点，120条主面板候选ID已冻结。未向原作者服务、R1或阿里云发送请求。

已读本地原作者快照`docs/sources/007_context_retrieval/packages/llm_judge/src/llm_judge/judge.py`：83–84行要求reasoning模型提供辅助LLM；385行起的reasoning路径先生成reasoning_content/content，再调用aux_llm做结构化提取，并有自己的格式失败重试规则。这与085直接解析原生JSON、成功不重发不同。010的source_notes与发布模型元数据记录辅助模型为量化Llama-3.1-8B。

010/078已运行的桥接是“原作者reference＋本研究Judge”，不是原Judge流程换V4。本地`scripts/replay_completed_research.py`也仅重放019–021保存结果，并非任意model profile的原作者在线Judge适配器；发布结果评价器按已有model/rater配置取数，不能凭换服务名产生新的Original-style结果。

因此当前不生成Original-style请求，也不部署Qdrant/BGE或另租辅助GPU。后续只有原提示、辅助提取接口、模型profile与成功/无效契约能完整且轻量冻结，并在用户确认API预算内，才可启动这项可选工作。替换辅助模型或跳过提取步骤均须明确记为管线差异，不称精确重现。不能据这里未接入就说原流程无法适配。

48条V4-B同期桥接另有可运行脚本与私有冻结请求，默认关闭；其目标仅是批次诊断，不冒充Original-style，不替换095原缓存。
