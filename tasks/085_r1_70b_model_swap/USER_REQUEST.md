执行任务085A：为 `DeepSeek-R1-Distill-Llama-70B` 的 AWS SageMaker JumpStart 模型替换实验完成部署前准备。

这是**部署前离线准备任务**。现在不要部署模型、不要调用任何 SageMaker 推理 endpoint、不要产生新的LLM/API推理费用，不自动开始正式085实验。完成准备、自检和交接后停止，等待用户手动部署endpoint并提供endpoint信息。

## 一、研究目的

我们需要排除一个重要混淆：

当前 `C48 → deepseek-v4-flash-0731 thinking-high → fixed four demonstrations(F4) → Frozen PriorG` 的收益，是否主要来自当前V4 Flash Judge能力不足。

计划用原VeriFact论文中表现最好的：

`DeepSeek-R1-Distill-Llama-70B`

做严格模型替换实验。

本任务不开发新算法、不调示例、不调PriorG、不做新的校准器。

正式实验应形成以下2×2结构：

- V4-B：现有084同期无示例结果，直接复用
- V4-F4：现有084固定四例结果，直接复用
- R1-B：未来新增
- R1-F4：未来新增

主问题：

1. R1-B raw是否明显强于V4-B或V4-F4；
2. F4在R1-70B上是否仍提供增量；
3. F4效应是否跨Judge模型存在；
4. Frozen PriorG直接作用于R1分数后的行为仅作为compatibility分析，不把它当R1公平最优校准。

## 二、固定正式评价队列

优先复用084已经冻结并完成同期B/F4评价的：

`outputs/084_f4_coverage_validation/sample_blind.jsonl`

即180条、21名development患者。

原因：

- 已有完全同期的V4-B/V4-F4结果；
- C48、claim、示例和评价代码均冻结；
- 不需要重新调用V4；
- 患者覆盖明显好于082新增7患者队列。

不得根据GT、V4正确性、文本长度或未来R1结果重新选这180条。

读取084协议、freeze、sample、new_predictions、evaluation_results和当前项目状态，核实ID、患者、C48 reference、B/F4模板和四个固定示例。

生成085自己的来源manifest和SHA绑定。

正式R1预测完成以前，不读取这180条GT用于方法选择、接口选择或解析规则选择。

## 三、构建provider-neutral的B/F4输入

从084冻结模板恢复：

- label定义；
- Judge任务说明；
- claim；
- C48 reference；
- five checks要求；
- 三分类评分要求；
- F4四个固定医生示例。

建立一个provider-neutral中间表示，不把阿里云特有字段直接耦合到SageMaker。

至少保存：

- proposition ID
- patient ID
- claim
- reference
- arm=B/F4
- system/instruction semantic content
- demonstrations
- expected output schema
- source SHA

不得改变四个示例内容、标签、顺序或C48。

### 注意

R1-Distill不是V4 Flash的 `enable_thinking=true` 接口。

因此不得把：

- `enable_thinking`
- `reasoning_effort`
- 阿里云专用 `response_format`

假定为SageMaker输入参数。

要把“研究语义条件”和“provider payload”分开。

正式endpoint的payload结构必须在部署后依据JumpStart提供的示例调用代码/真实preflight确定，不能现在凭猜测写死。

## 四、R1 tokenizer长度审计

仅下载/缓存：

`deepseek-ai/DeepSeek-R1-Distill-Llama-70B`

的tokenizer及必要配置文件。

**禁止下载70B模型权重。**

在任务专用环境中计算180条的B/F4输入长度，至少报告：

- min
- median
- p90
- p95
- max

分别报告B和F4。

如果tokenizer自带chat template：

- 保存template版本/hash；
- 用该template给出估算长度。

另外保留纯文本序列化长度用于诊断。

报告在以下假设下的上下文余量：

- 8K
- 16K
- 32K
- 64K
- 128K

并分别预留：

- 4096 output tokens
- 8192 output tokens

不得自动截断claim、C48或F4。

如果未来部署的实际context不足，正式实验应停止并报告，而不是静默裁剪输入。

## 五、准备SageMaker provider adapter

新增独立的AWS/SageMaker调用模块，不破坏现有阿里云客户端。

配置只从环境/CLI profile读取，例如：

- `AWS_REGION`
- `AWS_PROFILE`（可选）
- `SAGEMAKER_ENDPOINT_NAME`
- `SAGEMAKER_INFERENCE_COMPONENT_NAME`（仅未来实际部署存在时使用）

默认区域计划为：

`ap-northeast-1`

### 认证原则

不得在源码、任务JSON、日志或git中保存：

- AWS access key
- secret access key
- session token
- bearer token
- 任何其他凭据。

优先使用boto3默认credential chain / AWS CLI profile / AWS SSO。

准备以下零推理诊断功能：

1. `aws sts get-caller-identity`等价检查；
2. `DescribeEndpoint`；
3. 检查endpoint是否为 `InService`；
4. 打印endpoint name、region、状态、variant等非敏感信息；
5. 绝不打印credential内容。

普通调用优先准备：

`boto3.client("sagemaker-runtime").invoke_endpoint(...)`

但payload builder保持可插拔。

同时预留流式接口适配：

`invoke_endpoint_with_response_stream`

仅在部署后确认该JumpStart container实际支持streaming时启用。

不要现在假设OpenAI-compatible `/openai/v1` 一定由本JumpStart container支持。

## 六、部署后preflight框架提前写好，但现在不执行

提供显式命令，例如：

`python ... preflight --allow-inference`

没有 `--allow-inference` 时绝不发送endpoint请求。

部署后preflight应分三阶段：

### A. 最短虚构请求

不用真实研究病例。

确认：

- endpoint可调用；
-返回HTTP成功；
- 实际response schema；
- 模型输出位置；
- finish/stop信息；
-是否有thinking/reasoning标记；
-usage信息是否存在；
-是否支持stream；
-是否支持temperature/max_new_tokens等参数。

### B. 3条固定研究preflight

在180条正式评价中，在读取GT之前，仅按ID哈希预先冻结：

- 1条短B
- 1条中位F4
- 1条最长F4

这些调用以后必须计入正式结果，不因为回答不好重新调用。

用于验证：

- 输入没有被截断；
-最长F4可以完整处理；
- JSON/最终答案可解析；
- 推理没有因context或输出上限截断；
-响应时间是否逼近SageMaker限制。

### C. parser冻结

根据A/B中真实response schema，只调整“provider解析层”。

不得根据GT或正确性调整prompt。

parser冻结后才允许正式发送剩余R1-B/R1-F4。

## 七、提前准备R1输出解析

必须完整保存原始endpoint response。

考虑R1可能出现：

- `<think>...</think>`
- reasoning与final answer混在content中
- JSON外额外文字
- JumpStart外层生成结果字段

parser应将：

1. raw response
2. reasoning部分（若明确可分）
3. final textual answer
4. final verdict
5. label scores（若有）
6. reason/checks（若有）
7. finish/truncation状态

分开保存。

但是：

- 不允许用GT修复parser；
- 不允许因为模型判断错误重新请求；
- HTTP200但最终核心字段不可解析时，按预先规则记invalid；
-不能从reason“猜”最终label；
-不得静默把NS/NA映射错误。

preflight阶段冻结parser后，正式实验不得因结果修改。

## 八、正式085的评价代码现在准备好

但本任务不要运行正式R1推理。

主评价优先级：

### Primary：raw verdict

因为本实验首先回答“换模型后Judge能力是否变化”。

报告：

- PA
- MCC
- AC1
- Macro-F1
- false-S /真实non-S
- S/NS/NA precision、recall、F1
- confusion matrix
- patient-level wins/losses/ties
- paired patient bootstrap

比较：

- R1-B vs V4-B
- R1-F4 vs R1-B
- R1-F4 vs V4-F4

### Secondary：同一固定decision rules

若R1确实返回三类scores，再辅助计算：

- U0
- U2
- Frozen PriorG

但明确：

Frozen PriorG来自V4历史评分分布，直接作用于R1只能表示compatibility，不是R1经过公平重新校准的最优工作点。

**禁止在085中重新拟合R1 PriorG。**

## 九、正式实验的关键解释

预先在协议中写清以下四种可能：

1. `R1-B >> V4-F4`且F4对R1无增量：
   之前的F4可能主要是在补V4 Judge能力不足。

2. `R1-B`更强且`R1-F4 > R1-B`：
   说明F4存在跨Judge增量，是后续示例方法研究最有利结果。

3. `R1-B≈V4-B`且F4在两边均正：
   F4更像任务层面的教学效应。

4. R1不如V4：
   原论文模型在当前C48/任务接口下并非更强，排除“简单换回70B即可”的疑问。

不因看到结果改变上述解释框架。

## 十、部署后用户需要提供的信息

准备一个 `POST_DEPLOY_HANDOFF.md`，明确告诉用户部署完成后只需要提供：

- SageMaker Endpoint Name
- AWS Region（预期 `ap-northeast-1`）
- 如果使用非default本地AWS profile：profile名称
- 如果JumpStart页面提供了“Sample inference code / request payload”，建议用户复制该非敏感示例给Codex
- 如果使用Inference Component，再提供component名称

**不要要求用户提供AWS Secret Access Key或把凭据发进聊天。**

本地凭据由AWS CLI/SSO自行配置。

## 十一、交付

创建独立任务目录，例如：

`tasks/085_r1_70b_model_swap/`
`outputs/085_r1_70b_model_swap/`

当前阶段至少交付：

- protocol_predeploy.md
- source_manifest
- frozen cohort manifest
- provider-neutral B/F4 prompt artifacts
- tokenizer_length_audit
- SageMaker provider adapter
- AWS auth/endpoint diagnostic script
- deferred preflight runner
- frozen parser framework
- evaluation framework
- POST_DEPLOY_HANDOFF.md
- selfcheck
- 中文preparation report

执行严格自检。

不得：

- 部署AWS endpoint；
- 调用SageMaker推理；
- 调用新的阿里云Judge；
- 使用reserved40；
- 读取评价GT来改方法；
- 修改历史冻结成果；
- 修改.gitignore；
- commit/push；
- 自动开始正式085。

常规代码和环境问题自行解决；若仅tokenizer获取失败，可记录具体原因并完成其余准备，不要因此改用其他70B模型。
