# 085A：R1-Distill-Llama-70B模型替换实验的部署前准备

**结项状态：离线准备完成，正式085尚未开始。** 新增LLM/SageMaker推理调用0次，新增推理API费用¥0；未部署endpoint，未使用reserved40，未读取180条评价GT做接口/方法/解析设计，未改084冻结成果、`.gitignore`或默认系统；本任务按用户明确要求不commit/push。

## 固定材料与交付

将084的180条／21名development患者、各一份B和F4冻结为360条[provider-neutral输入](neutral_jobs.jsonl)。保留原C48 reference、claim、Judge标签定义、五项核查、三分数目标及四个医生示例的内容/标签/顺序；[来源manifest](source_manifest.json)绑定084 sample/jobs/freeze、071示例及084结果文件SHA。V4-B/F4未来直接复用084同期回执，不重新调用。071教学患者候选池与本队列有121条／14人重叠，另外59条／7人在池外；这仍是已暴露development，不是独立新测试。

AWS独立[adapter](../../tasks/085_r1_70b_model_swap/sagemaker_provider.py)使用boto3环境/CLI profile，含STS和DescribeEndpoint只读诊断、`InService`检查、普通runtime及受验证约束的stream接口。payload保持插件化，未根据阿里云`enable_thinking`/`reasoning_effort`/`response_format`猜JumpStart容器字段。[延后预检](../../tasks/085_r1_70b_model_swap/deferred_preflight085.py)必须显式`--allow-inference`；目前无部署样例插件、无endpoint配置、没有执行A/B收费请求。A为虚构病例；B的三个固定ID见[预选清单](preflight_selection.json)，未来成功回答计入正式结果。C只根据A/B原始返回冻结provider解析路径。

[解析器](../../tasks/085_r1_70b_model_swap/parse_r1.py)保留原始回执、分离明确的`<think>`、final文本、verdict、有效三分数、reason/checks及finish；只从明确最终JSON verdict取类别，输出截断、未闭合thinking或核心字段不可解时记invalid。未来由[GT盲预测物化器](../../tasks/085_r1_70b_model_swap/materialize_predictions085.py)在冻结parser下生成360行预测。[评价框架](../../tasks/085_r1_70b_model_swap/evaluate085.py)已写但未运行，未来以四臂共同有效ID为raw主分析，用项目统一`evaluate`/`paired_compare`及1000次患者bootstrap；无效/缺失保持180固定分母并单列。R1有效三分数的U0/U2/Frozen PriorG仅是次级兼容性，不重拟合R1。

## Tokenizer长度与可行性边界

仅缓存官方`deepseek-ai/DeepSeek-R1-Distill-Llama-70B`修订`b1c0b44b4369b597ad119a196caf79a9c40e141e`的四个tokenizer/配置文件，未下载70B权重。用该revision的chat template、`add_generation_prompt=True`逐条计数，另保留纯文本计数；均无截断。[完整分布、纯文本长度与上下文余量](tokenizer_length_audit.md)。

| 输入 | min | median | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|
| B chat | 2592 | 3195.5 | 3391.2 | 3439.8 | 3918 |
| F4 chat | 8368 | 8971.5 | 9167.2 | 9215.8 | 9694 |

8K上下文连F4输入都放不下；16K加4096输出预留可容纳全部F4，但加8192预留为0/180；32K及以上在这两种预留下均可容纳全部。官方`config.json`给`max_position_embeddings=131072`，tokenizer元数据给`model_max_length=16384`；实际JumpStart容器限制未知，不能据较大值开跑。若实际context不足，停止、不裁剪claim/C48/F4。

## 决策与剩余条件

085A只证明材料和代码可离线冻结，**没有模型性能结论**，也无法预告R1是否优于V4。下一步由用户手动部署并提供[交接清单](../../tasks/085_r1_70b_model_swap/POST_DEPLOY_HANDOFF.md)中的非敏感endpoint/region/profile/可选component及JumpStart示例调用代码。随后先做只读诊断，再另行核算endpoint持续运行成本、actual context、调用schema、超时与正式085费用，才可能执行A/B和剩余R1调用。不能把官方模型config长度当成容器验证，也不能把072/084的development收益当作跨模型结论。

[离线自检](selfcheck.json)：2194项PASS（材料SHA、180/21、360输入、四示例、tokenizer文件白名单、三例预选、解析合成例、AWS mock gate、`.gitignore`未改）；独立审计未执行。

官方参考：[JumpStart可用模型目录](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models-latest.html)、[InvokeEndpoint](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html)、[DescribeEndpoint](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeEndpoint.html)、[官方模型文件](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-70B/tree/b1c0b44b4369b597ad119a196caf79a9c40e141e)。
