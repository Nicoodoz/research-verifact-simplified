# 085A：R1-Distill-Llama-70B 模型替换部署前协议

状态：`PREDEPLOY_OFFLINE_ONLY`。2026-09-26，起始HEAD `d86ea7c21b6fd21a8b0c0a9a55a535009e26cd03`。085A只冻结材料、审计tokenizer长度、准备AWS诊断、provider adapter、延后preflight、解析和评价代码；**不部署endpoint、不发SageMaker或其他LLM推理、不读取084评价GT做任何设计决定、不启动正式085**。本阶段新增推理API费0元。用户本次明确要求不commit/push，覆盖先前一般推送约定。

## 固定研究条件

- 目标：仅换Judge为JumpStart `deepseek-llm-r1-distill-llama-70b` 对应的 `deepseek-ai/DeepSeek-R1-Distill-Llama-70B`，不改C48、claim、B/F4语义、四例、Frozen PriorG、样本或标签。
- 队列为084 `sample_blind.jsonl` 固定180条／21 development患者，V4-B/V4-F4复用084保存的同期答案。R1未来各180条；不得按GT、V4正确性、长度或R1结果改选。
- B系统语义取084完整system内容，F4系统语义是B原文加原四例块。084 user 内容JSON中的proposition/reference保持原值。原JSON评分与five checks要求作为语义目标，SageMaker具体字段、messages封装、生成参数、response schema需未来按部署样例和真实preflight确认。
- 084队列已暴露development，071选例训练患者池与其中121条／14患者重叠，池外59条／7患者；不能称新独立测试。实际四例患者与评价患者隔离。

## 部署后两阶段接口及解析冻结

先用独立的只读AWS身份/DescribeEndpoint诊断确认endpoint `InService`。实际endpoint name、region（预期`ap-northeast-1`）、可选profile、可选InferenceComponentName均由环境或CLI提供，不写入冻结任务JSON。SageMaker `InvokeEndpoint`格式由部署后的JumpStart Sample inference code和虚构A阶段真实回执决定；`InvokeEndpointWithResponseStream`仅确认容器支持后启用。085A提供的payload插件接口默认未实现，缺失插件或`--allow-inference`则不发送。

未来preflight A是最短虚构请求，用于确定容器payload、外层返回、finish、usage、stream与生成参数兼容性。B阶段只使用预冻结的短B、中位F4、最长F4各1条，不读GT；这3条属于正式180×2对应位置的第一次答案，绝不因回答内容重发。若最长F4及预留输出超实际context，或发生截断／超时，停止正式发送，不裁剪。C阶段仅基于A/B原生回执冻结provider envelope路径、thinking/final分离与核心字段解析，不用GT修补。HTTP200核心无效计invalid，不从reason猜标签；模型判断错不重发。正式调用的费用与endpoint运行时长须另行批准和登记，085A不授权推理。

## 评价框架（此阶段不执行）

四臂为V4-B、V4-F4、R1-B、R1-F4。**Primary为raw verdict**，同180 ID用统一`evaluate`和`paired_compare`、valid-only命题micro、1000次患者cluster bootstrap；主比较R1-B vs V4-B、R1-F4 vs R1-B、R1-F4 vs V4-F4，另给F4跨模型效应差的患者bootstrap。报告PA/MCC/AC1/Macro-F1、错误支持/真实非S、三类P/R/F1、混淆矩阵、救回/伤害及患者胜负。缺失/invalid保持冻结分母并单列，正式配对主指标仅在事前定义的完整共同有效集合上报告，同时给全队列覆盖及缺口，不静默补临床标签。

R1若返回有效三分数，Secondary才离线给U0/U2/Frozen PriorG兼容性；不拟合R1 PriorG，不将V4历史校准视为R1最优。R1无有效评分时不把raw标签伪造成三分数。

解释在结果前登记：①R1-B明显强于V4-F4而R1-F4无增量，支持“V4能力限制”解释；②R1-B更强且R1-F4再提高，支持跨Judge示例增量；③R1-B≈V4-B且两Judge的F4均正，符合任务教学效应；④R1弱于V4，说明原论文模型在本C48及实际接口下不保证更强。以上均须兼看类别损失、false-S、重复与成本，点估计/解释不等于内部因果证明。

不使用reserved40、不改历史冻结成果或`.gitignore`、不提交推送、不自动运行正式085。用户部署并交付endpoint元信息之前，所有推理路径保持关闭。
