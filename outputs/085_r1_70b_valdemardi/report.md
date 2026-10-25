# 085 Valdemardi运行接入与A/B预检报告

**状态：A/B完成，正式批量未获授权、未启动。** 2026-09-27；本轮0次评价GT读取、0次V4重跑、0次reserved40调用。所有目标请求沿用085A冻结的084队列与B/F4消息，仅替换Judge模型名。F4四例身份、内容及顺序均未变。当前默认C48→DeepSeek T-S→Frozen PriorG不变。

## 研究边界与身份

本次实际服务为`Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ`，用户报告运行于A800 80GB、vLLM 0.10.1.1；本机loopback `GET /v1/models` HTTP200返回该唯一模型ID与`max_model_len=20000`，原生回执及SHA已保存。公开Valdemardi仓库revision为`ebfea7be35ca86beee303282386399416205c306`，配置的4-bit AWQ参数与旧Casperhansen目标相同。**服务名不足以独立证明远端权重字节、revision、GPU或vLLM版本**；这些仍是用户部署记录。相同基础家族及AWQ配置不意味着同一仓库checkpoint，更不意味着原VeriFact完整流水线的逐字节复现。旧085A、Casperhansen 0.9.2及AWS工件未改写。[Valdemardi公开仓库](https://huggingface.co/Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ/tree/ebfea7be35ca86beee303282386399416205c306)

新运行配置和360条请求哈希见[profile.json](profile.json)，模型列表的私有原始回执与公开摘要见[service_identity.json](service_identity.json)。任务代码只接受`127.0.0.1/localhost/::1`的`http://.../v1`，禁用代理与重定向。原生临床请求/回执在现有忽略目录`.local_models/085_valdemardi_private/`，公开工件仅含ID、哈希、长度及汇总指标。

## Tokenizer兼容性

085A使用官方固定revision；Valdemardi当前公开`tokenizer.json`、`tokenizer_config.json`及chat template SHA均不同。新模板SHA为`b6835114b7303ddd78919a82e4d9f7d8c26ed0d7dfc36beeb12d524f6144eab1`，旧模板为`56a1447ad31926fdc21fb07e56e5642bd9c850c4f52d8c8af7bbe5f079a84f5f`；新模板对全部360个原样消息的本地计数恰好少2 token。B输入范围2590–3916，F4为8366–9692；全部本地输入加8192输出上限不超过20K。tokenizer元数据为16384，实际服务模型卡为20000；所选最长输入本身低于16384，输入加输出预算按实际服务20K检查。[兼容性审计](compatibility.json)保存了公开配置SHA与AWQ参数比对。

Stage A及三条Stage B的服务`usage.prompt_tokens`分别为567、2590、8969、9692，与本地Valdemardi模板计算逐条相等。三条代表性真实请求没有观察到静默输入截断；其余357条只有本地长度预测，正式运行仍需逐条检查。没有用旧官方token数作为当前服务的硬门槛，也没有裁剪输入。

## A/B原生观察

|阶段|固定角色|HTTP|输入token|完成token|耗时秒|finish|raw有效|分数有效|
|---|---|---:|---:|---:|---:|---|---|---|
|A|纯虚构|200|567|583|18.235|stop|是|是|
|B|short B|200|2590|725|24.625|stop|是|是|
|B|median F4|200|8969|645|28.875|stop|是|是|
|B|longest F4|200|9692|1009|36.797|stop|是|是|

四次均首次HTTP200、无重试，`reasoning_content`、最终`content`、`finish_reason`、`usage`、`model`均在原生回执中。Primary raw标签只从最终`content`解析；`reasoning_content`仅存档。raw标签和三类`label_scores`分别验效，三条Stage B两者均有效；没有依据GT评判或选择输出。最长F4的`9692+8192=17884`，距20K还余2116 token。三条B首次成功回答已占据正式360位置，不会重发。

逐条公开摘要：[Stage A](stage_a.json)、[short B](stage_b/short_B.json)、[median F4](stage_b/median_F4.json)、[longest F4](stage_b/longest_F4.json)。[请求台账](request_ledger.json)登记4次推理及3次`/models`探针，全部HTTP200、0重试、0未知回执；请求、响应SHA和wall-clock也在私有append-only尝试链。

## 批量时间与费用预测

剩余R1-B **179**、R1-F4 **178**，客户端实测并发为1。用B的24.625秒均值及F4的28.875/36.797秒均值外推，串行约**10,252.683秒（2.85小时）**；增加50%规划余量约**15,379.024秒（4.27小时）**。最长单次36.797秒。详见[forecast.json](forecast.json)。样本仅三条，生成长度、prefix cache、负载、启动和闲置时间可能显著改变实际耗时；50%不是费用硬上界。

当前实例真实小时单价没有提供，因此GPU租金和正式批量人民币费用**未知**，不沿用历史¥5.88/小时。接口是用户管理的AutoDL本机vLLM，未取得独立按请求API计价；这不等于GPU使用免费。预检4次的GPU租金同样无法据此计价。

## 自检与决定

[自检](selfcheck.json)：61项PASS；5项离线单测PASS。核对旧freeze、360条消息仅模型名变化、原085A三例选择、回执与SHA、服务token、20K余量、首次HTTP200、不公开临床原文和正式边界。独立审计未执行。

**决定：当前仅证明Valdemardi服务和冻结B/F4请求在所选A/B上技术兼容。** 尚无R1系统成绩、患者外比较或相对V4的收益结论。下一步由用户查看时间预测、提供本实例实际时价并另行授权后，再安排剩余357条；届时按冻结同ID比较R1-B/V4-B、R1-F4/R1-B、R1-F4/V4-F4及两Judge的F4效应。主分析用raw verdict；PA、MCC、Gwet AC1、Macro-F1、三类P/R/F1、混淆矩阵、false-S、rescue/harm、患者胜负平及1000次患者cluster bootstrap均按085A口径；只有真实分数有效的行才做U0/U2/Frozen PriorG次要兼容性分析，不重拟合PriorG。
