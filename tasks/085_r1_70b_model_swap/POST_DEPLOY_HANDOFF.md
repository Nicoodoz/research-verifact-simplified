# 085A 部署后交接（当前仍为零推理）

085A已完成离线准备，**没有部署或调用endpoint**。请用户手动部署官方JumpStart `deepseek-llm-r1-distill-llama-70b` 后，仅提供：

1. SageMaker Endpoint Name；
2. AWS Region（计划 `ap-northeast-1`，以实际部署区域为准）；
3. 若非 default，本地 AWS profile 名称；
4. 若使用 Inference Component，其名称；
5. JumpStart 页面非敏感的 *Sample inference code / request payload*，尤其是 `Body`、`ContentType`、`Accept`、生成参数、返回格式和容器限制。请删除示例里的账号、凭据、真实病例内容。

**不要把 AWS Access Key、Secret Key、Session Token 或其他凭据发进聊天或写入仓库。** 本地用 AWS CLI profile/SSO 或 boto3 默认凭据链。部署费用、区域支持、实际context、容器payload和streaming能力尚未验证。

## 可先执行的零推理诊断

在仓库根目录，设置环境变量 `AWS_REGION`、`SAGEMAKER_ENDPOINT_NAME`，可选 `AWS_PROFILE` 和 `SAGEMAKER_INFERENCE_COMPONENT_NAME`。下述命令只做 STS、DescribeEndpoint（如配置component，另DescribeInferenceComponent），不会调用runtime：

```powershell
& .local_models/085a_tokenizer_venv/Scripts/python.exe tasks/085_r1_70b_model_swap/sagemaker_provider.py --live
```

输出仅含遮蔽后的账号末四位、身份类型、endpoint状态/variant等。若AWS凭据链尚未配置，先在本地完成AWS CLI/SSO配置；无需向Codex暴露密钥。

## 后续085的门槛（现在不要运行收费步骤）

从实际Sample inference code建立**部署专用** `build_payload(job, settings) -> (bytes, content_type, accept)` 插件。默认没有插件，也不猜测OpenAI兼容或JumpStart JSON结构。先检查容器真实最大context、输出长度和超时；F4最长输入估算9694 tokens，16K上下文加8192输出预留放不下。若容器限制不足，停止并记录，不截断证据。

阶段A仅虚构病例，阶段B为`preflight_selection.json`固定的三个GT盲真实ID；其成功回答直接计入正式085，绝不因内容不满意重发。以下是**以后正式授权执行**的入口形式，当前085A没有执行：

```powershell
& .local_models/085a_tokenizer_venv/Scripts/python.exe tasks/085_r1_70b_model_swap/deferred_preflight085.py A --payload-plugin <deployment-plugin.py> --allow-inference
& .local_models/085a_tokenizer_venv/Scripts/python.exe tasks/085_r1_70b_model_swap/deferred_preflight085.py B --payload-plugin <deployment-plugin.py> --actual-context <verified-token-limit> --output-reserve <verified-output-limit> --allow-inference
```

不加`--allow-inference`会只打印计划，调用数为0。A/B原始返回保存为`outputs/085_r1_70b_model_swap/deferred_preflight/*.raw`，不打印临床文本。根据实际返回创建只含envelope路径的`CANDIDATE_FROM_AB_NO_GT` JSON，通过阶段C冻结解析；不读取GT、不用模型答对与否改规则。仅冻结后才能规划剩余357个R1请求和单独费用授权。SageMaker endpoint持续运行成本需要另行核算；085A没有建立或收费使用endpoint。

正式预测全部齐备后，建立360行`receipt_index.jsonl`（`id`、`sid`、`arm`、相对仓库根目录的`raw_response_path`、经部署元数据核实后的`model_verified:true`），用`materialize_predictions085.py`按冻结parser生成GT盲预测；`evaluate085.py`再检查全360个固定ID/arm、原生raw SHA和parser指纹，在同一共同有效队列上调用项目统一评价器。这两步本阶段都没有运行。
