# 103方法、接口与历史经验说明

本轮是开发选型与小规模可训练性验证，尚非论文确认。092的encoder顶部训练确有同输入增量，但主要救回S、NS召回仍低；因此不能以训练后PA或相对低起点涨幅选底座。096提示旧vLLM量化/算子部署差异会显著影响速度，本轮不继承其环境或精度；097支持简洁原作者式任务作为合理强接口，但不能将不同任务/模型的历史值当训练增量。099的自然选型和少数类压力结果不一致，103扩大固定选型面板并增加直接输出对照。101未获得NS/NA净收益；102只在构造阶段停止，其预算解释已更正并依用户指令封板，不恢复。

## 来源及价格（2026-10-27只读核对）

[千问AI官方模型价格](https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices)：输入/输出元每百万token为qwen3.5-27b 0.6/4.8、qwen3.8-27b 3/12、qwen3.5-35b-a3b 0.4/3.2、qwen3.6-35b-a3b 1.8/10.8；前两种3.5价格适用于≤128K输入，本轮实际远低于此。3.8缓存优惠只用于实际usage对账，预算统一不假定命中，也不使用渠道1/6折扣。四候选在实际端点/models均有明确ID；9B无明确型号与目录单价，不发收费探针，不用Flash替换。

[官方Chat参数](https://platform.qianwenai.com/docs/api-reference/chat/openai-chat)明确3.8的thinking_budget4096映射low；不能同时传reasoning_effort。四模型同4096思考上限与768最终输出，但预算相同并不保证内部推理行为相同。思考用满而最终JSON正常结束与最终回答被截断不同；分别记录reasoning_tokens、finish_reason、格式及实际总completion_tokens。部分usage的text_tokens字段可能重复总completion含义，费用不把它和reasoning_tokens再相加。

官方权重来源：[9B](https://huggingface.co/Qwen/Qwen3.5-9B)、[3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B)、[3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)、[3.5-MoE](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)、[3.6-MoE](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)。revision及tokenizer/template/config/index的SHA已保存在model_metadata.json。API实际权重revision、精度及内部模板无法独立验证；本地固定BF16，必须做小桥接，不能从云端成绩直接减本地成绩计算微调增量。

## 训练实现选择

[Unsloth官方Qwen3.5指南](https://unsloth.ai/docs/models/qwen3.5/fine-tune)提供BF16 LoRA及MoE支持；[PEFT官方LoRA文档](https://huggingface.co/docs/peft/en/package_reference/lora)说明专家原始Parameter与普通Linear的目标方式不同。本轮预备代码核查两种实现下的专家覆盖、LoRA实际更新及视觉冻结。Unsloth最新版依赖声明限制Transformers≤5.17，故没有盲装当时最新5.21；按Linux/Python3.12完成解析并hash锁定，实际GPU导入/算子待第二阶段确认。

普通梯度检查点用于省激活，不默认启用权重CPU卸载、4bit或全参训练。微批1无padding，完整prompt loss均为-100，真实verdict JSON及结束标记参与loss；不训练医生理由或模型思维链。全部监督与评价患者隔离，历史100患者暴露如实保留。

[PyTorch Blackwell支持说明](https://pytorch.org/blog/pytorch-2-7/)是CUDA12.8路线依据；[AutoDL计费说明](https://www.autodl.com/docs/price/)说明开机而非仅GPU运算计费，关机后付费数据盘仍可能收费。运行前核实实际实例单价、开机时间和存储成本；预算/计时从加载、安装及编译前开始。
