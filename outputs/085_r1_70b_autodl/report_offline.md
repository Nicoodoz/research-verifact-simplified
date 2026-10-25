# 085恢复：AutoDL/vLLM分支离线准备报告

**状态：`AUTODL_OFFLINE_READY_AWAIT_USER_ENDPOINT`，正式085未完成。** 已完成新provider adapter、远端启动/manifest脚本、tunnel说明、A/B预检与单独正式授权门槛、GPU时间账本、评价接入、离线测试及dry-run。没有租实例、连接SSH、访问AWS、下载权重或执行任何推理。当前进程没有R1_BASE_URL，用户尚未提供实际远端manifest与小时单价，因此不能给出真实A/B结果、吞吐或租金预测。

开始时本地与远端main均为`529d288a45faad40bf9adb953bbbdb96bc9ea721`，工作区干净。历史085A全部文件和原暂停记录原位保留，089交付哈希逐文件核对不变；`.gitignore`与默认系统不改。新路线是用户手工租用/管理AutoDL，通过用户本地SSH tunnel接OpenAI-compatible服务，不使用旧SageMaker adapter。最新恢复指示覆盖旧“R1暂停”的当前含义，旧记录仍准确描述当时状态。

## 1. 模型身份核实到了哪一步

原VeriFact固定代码revision `f115d36cb65fa2073fce0a10df56bb37f4cbcd50`的[r1-70b配置](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/configs/inference/r1-70b.env)确实指定用户给出的AWQ仓库与官方tokenizer名字。其[docker-compose](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/docker-compose.yml)使用vLLM0.9.2，并有TP2及TP1服务配置。因此不能笼统断言原研究只有一种TP运行方式。

本轮通过公开HF metadata得到并冻结：

|项目|冻结身份|
|---|---|
|模型|`casperhansen/deepseek-r1-distill-llama-70b-awq`|
|resolved model revision|`a1ab7653aae77fbabc536cbcbac5bb2e2fb5354f`|
|tokenizer|`deepseek-ai/DeepSeek-R1-Distill-Llama-70B`|
|tokenizer revision（沿085A）|`b1c0b44b4369b597ad119a196caf79a9c40e141e`|
|quantization config|AWQ，bits4、group_size128、zero_point=true、version=gemm|
|权重清单|9个safetensors，共39,767,996,432字节；只获取公开大小/SHA，没有下载|

[身份目标与来源](identity_target.json)、[远端便携lock](../../tasks/085_r1_70b_autodl/identity_lock.json)、[公开原文件](public_sources/)。AWQ仓库自带tokenizer与官方tokenizer并不相同；本轮显式指定官方tokenizer及revision，保留085A输入长度语义。

**远端实际权重身份仍未验证。** 远端脚本会对预置目录的全部目标权重/config逐文件核对公开内容哈希，并记录resolved revision、实际路径、配置、版本、GPU与完整启动参数。不同checkpoint立即停止，不仅检查服务名字。原VeriFact配置没有pin其当时HF revision，因此当前能建立的是相同公开AWQ checkpoint目标与本轮固定版本，不能证明原论文运行时历史权重的逐字节一致性。

## 2. 固定输入与运行配置

085A冻结180条/21名development患者、B/F4各180份中立材料完整复用，没有按GT/成绩/长度重新选样。V4-B/V4-F4正式评价将直接复用084同期回执，不新增V4请求。只生成新的R1请求封装，原system语义、目标claim/C48、四例内容/标签/顺序逐条核验。客户端固定temperature0、top_p1、max_tokens8192，原生保存reasoning_content/content，不加辅助Llama-8B或任何LLM解析。

远端使用直接Python vLLM服务，无Docker依赖。固定vLLM0.9.2、VLLM_USE_V1=1、dtype auto、max_model_len20000、gpu_memory_utilization0.90、TP1/PP1、block16、swap4、prefix caching、scheduler steps1、max_num_seqs4、enable_reasoning、deepseek_r1。0.9.2源代码仍接受[已弃用enable-reasoning](https://github.com/vllm-project/vllm/blob/v0.9.2/vllm/engine/arg_utils.py)，实际reasoning parser另明确指定。

max_num_seqs4是服务吞吐/显存调度配置，不是模型语义参数；客户端仍从串行1开始，不能把服务允许4个序列直接当成已经实测的四倍吞吐。

与原服务/研究pipeline需明确列出的差异：单GPUTP1与低max_num_seqs4；本轮temperature0/top_p1/max_tokens8192；官方tokenizer固定revision；当前研究B/F4提示而非原VeriFact整套Judge提示；不使用原辅助结构化模型；客户端不增加guided JSON强制解码，而是依原提示要求解析实际最终JSON。server额外使用generation-config vllm防止HF generation_config默认采样覆盖（[官方说明](https://docs.vllm.ai/en/v0.9.2/serving/openai_compatible_server.html)），并关闭请求文本日志。所有差异进入实际manifest，不包装成完整原VeriFact pipeline复现。

长度继续用085A官方tokenizer：B2592–3918、F48368–9694；最长F4加8192输出预留=17886，距20000有2114余量。这里只证明离线估算可容纳，**没有证明单A800真实显存或吞吐可行**。A/B必须验证实际prompt_tokens、finish与无截断；不能裁剪claim/C48/F4。

## 3. API与GPU账目、正式运行门槛

本轮新付费项目API调用0，API费用0。AutoDL实例是否已由用户租用、何时开始、小时单价均未获知，GPU租金记null/未知，不能伪称0，也不沿用20元API上限充当GPU预算。独立runtime_ledger记录实例与服务起止、实际用户单价；正式run另外保存墙钟。服务/推理时间属于实例区间，不叠加算租金。

模型及缓存默认数据盘`/root/autodl-tmp/huggingface`，并固定HF_HUB_CACHE避免继承系统盘缓存。预置权重优先验证、复用；无缓存仅在用户远端显式download-if-missing时下载，先检查空间。项目不存SSH密码、AutoDL token或其他凭据。

A虚构病例先验证/models及真实envelope；B固定short_B、median_F4、longest_F4，第一份HTTP200计入360。成功回答即使核心无效也不重发；无成功响应的短时故障最多3次有限恢复。A/B都通过结构/长度/截断检查后，从实际返回路径冻结原085A parser，无GT修补。

B结束输出剩余臂位（通常357）的串行时间、50%规划余量、实测completion和实际小时价格对应的费用预测；3例估算不是保证上界。**到此必须等待用户明确授权正式批量**。formal需现有forecast/parser、明确授权说明、实际单价、允许运行小时数；默认客户端并发1，未实测并发收益时不扩大。没有自动烧完整A800时间的路径。

## 4. 评价已准备，但没有新模型成绩

保留085A统一evaluate/paired_compare及1000患者cluster bootstrap：PA、MCC、Gwet AC1、Macro-F1、三类P/R/F1、混淆矩阵、false-S/non-S、救回/伤害与患者胜负平。主比较R1-B−V4-B、R1-F4−R1-B、R1-F4−V4-F4，另报两个Judge各自F4效应及效应差。

Primary为raw，共同有效集合与固定180分母的invalid/缺失分开；R1不使用历史标签补洞。只有有效原生三分数才运行secondary U0/U2/Frozen PriorG，不拟合R1专属先验。当前无R1推理，所有性能、吞吐、租金预测均未测；没有空表填0或虚构结果。

## 5. 自检、下一命令与当前交付边界

离线自检**2308项PASS**，另**11项合成测试PASS**；原始085A与089字节核对、360请求语义、来源/身份锁、三例冻结、成功请求复用、3次恢复链、正式授权门槛、无scores不伪造、GPU账目空值等已检查。两个bash wrapper通过语法检查；远端启动命令与本地请求分别dry-run，均0网络/0推理。**尚未在真实Linux/vLLM/GPU服务运行，独立审计未执行。** 自检通过不等于GPU已可部署。

用户下一步按[AutoDL操作说明](../../tasks/085_r1_70b_autodl/AUTODL_HANDOFF.md)准备远端、复制脚本、建立tunnel，并提供非敏感的本地地址、实际manifest/observation文件路径和小时价格。无需提供密码或token。目前可直接运行的零推理命令：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/085_r1_70b_autodl/runner.py dry-run
```

研究状态已从旧`PREDEPLOY_READY_PAUSED_BY_USER`恢复到AutoDL离线准备。正式085尚未完成，依据用户“085完成后提交推送”的本轮约定，**当前没有commit/push**；不把本阶段冒充正式结项。所有本地成果可审阅和继续使用，不自动启动其他研究任务，不改变089/历史冻结文件、.gitignore或默认系统。
