# 085夜间暂停与待同步差异

本090任务期间085、AutoDL、AWS、R1-70B全部暂缓，不访问localhost:8000/18000或任何已有练习服务，不下载权重、不改SSH/电源。不认为用户已有1.5B服务就是正式Judge。

仓库085 AutoDL已交付代码仍锁定`casperhansen/deepseek-r1-distill-llama-70b-awq`与vLLM0.9.2，身份锁、启动脚本、旧AWS材料及暂停记录均保持原样。

用户在090最新指示中说明：之后已接受ModelScope的`Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ`与现成vLLM0.10.1.1，不再要求跨仓库全部tensor逐字节相同。这是用户最新研究决定的恢复备忘，不是今晚已经验证该服务或修改了085实现。

未来用户清醒并另行恢复085时，需把新授权与旧冻结代码明确分支/同步，记录真实checkpoint/revision、tokenizer、quantization、vLLM/runtime/GPU/完整启动参数；核实实际tokenizer长度、上下文/输出截断、显存、推理参数、吞吐及小时费用。不能继续拿旧Casperhansen精确哈希gate阻挡用户已接受的新模型，也不能把新checkpoint称为已证明与原VeriFact所有权重相同。

今晚没有部署、预检、推理、平台管理或费用试探。090的40元仅本次阿里云API总上限，不是085的GPU租赁预算。
