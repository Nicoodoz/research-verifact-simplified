# 099候选核对（2026-10-26，分类前）

本任务只调用现有千问AI平台API。以下公开权重只读取模型卡、config、生成配置、chat_template和权重索引及revision，没有下载权重、安装环境或访问AutoDL。[官方源文件指纹](../../outputs/099_judge_selection/official_source_manifest.json)、[机器可读模型元数据](../../outputs/099_judge_selection/model_metadata.json)。

|API候选|输入/输出元每百万token|对应公开权重|BF16权重索引总量|单A80080GB高保真取舍|
|---|---:|---|---:|---|
|qwen3.8-flash|0.8 / 2.7|Qwen3.8-Flash-Next，官方称API基于此版本|约360GB|完整BF16显著超80GB；4bit仅原始参数仍约90GB。CPU卸载/剪枝/重量化不是已验证同权重单卡方案，保留API参考，不作为本轮单卡高保真主候选|
|qwen3.8-27b|3 / 12|Qwen/Qwen3.8-27B，Apache2.0|约55.56GB|27B dense，BF16有较多显存余量；仍须验证实际vLLM版本、混合注意力、KV/SSM状态与目标输入长度|
|qwen3.5-27b|0.6 / 4.8|Qwen/Qwen3.5-27B，Apache2.0|约55.56GB|同为dense BF16，较方便直接单卡；价格明显更低，质量由同ID实验决定|
|qwen3.5-35b-a3b|0.4 / 3.2|Qwen/Qwen3.5-35B-A3B，Apache2.0|约71.90GB|MoE仍须加载全部专家，不能按激活3B算显存；text-only、低并发和限定context下可能可行，但显存/工作区余量较紧|

价格来自[新平台全模型价格表](https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices)。后两个价格针对输入≤128K，较高档位已写进执行器预留与结算；不假定它们有未列出的缓存优惠。Flash和3.8-27B隐式缓存输入分别0.1/0.6元每百万token。本次不等待峰谷价。

[Flash-Next官方模型卡](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)说明与API Flash的关联；它约125B主模型、51B n-gram embedding及4B MTP，采用新稀疏架构，不能拿某个27B checkpoint或裁剪版冒充同一个API。其许可证也与三个小模型不同，见相应公开卡。

三个小模型均有视觉编码器，但本任务纯文本。config声明BF16，27B类有64层、16个全注意力层、4个KV头及head_dim256；35B类40层、10个全注意力层、2个KV头。纯注意力BF16 KV粗算每token约64KiB/20KiB，32K约2GiB/0.625GiB；这不包含线性注意力状态、CUDA上下文、图缓存和MoE工作区，不能将粗算当部署实测。建议首先使用官方BF16、单并发、text-only、关闭投机/MTP，不先上FP8或4bit；A800的Ampere条件不能照搬Hopper原生FP8吞吐。框架/量化硬件支持应以[官方vLLM矩阵](https://docs.vllm.ai/en/latest/features/quantization/)和[Qwen配方](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)为准，当前不复用或升级冻结旧GPU环境。

[3.8-27B模型卡](https://huggingface.co/Qwen/Qwen3.8-27B)、[3.5-27B模型卡](https://huggingface.co/Qwen/Qwen3.5-27B)、[35B-A3B模型卡](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)提供架构、能力和服务用法。四模型均可文本/思考核验，但通用或医学知识问答benchmark不等于患者EHR三分类能力；本轮不依此指定胜者。

**API精度与精确revision仍unknown。**公开文件BF16不证明阿里云当前服务采用BF16、同一权重revision或同一模板/算子。模型同名也不保证greedy逐条一致。3.8-27B支持low/medium/xhigh，本轮统一thinking_budget2048并由API映射为low，不同时传reasoning_effort。两个3.5模型同样使用该2048预算。512 max_tokens只管最终回答，思考另计；参数依据[当前Chat API](https://platform.qianwenai.com/docs/api-reference/chat/openai-chat)。

之后的小样本API/A800桥接必须核对权重revision、tokenizer/模板SHA、实际输入长度与thinking预算实现，记录差异而非强称平台科学等价。详细计划随最终推荐给出。
