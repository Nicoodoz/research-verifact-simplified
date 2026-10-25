# 055 Protocol Amendment 001：Full Qwen second opinion extension

初始055协议限定0新增LLM调用，只利用既有DeepSeek scores做zero-label prevalence-conditioned policy adaptation。初始实验完成后，结果显示仅依赖DeepSeek score/prior的自适应跨052/053不稳定。用户随后明确要求：不限制实现方法，目标是实现新环境zero-label adaptation。

因此055扩展一项额外target-unlabeled信息源：对052/053各240条claim获取同一reference下的Qwen3.8-27B non-thinking scoring second opinion。请求payload不包含GT、author或历史预测结果；Qwen只读取proposition/reference。已有Gate候选Qwen结果逐条body hash一致时复用。

冻结执行：
- 052：240 total，22 reuse，218 new；
- 053：240 total，29 reuse，211 new；
- 合计429个新API调用、51个复用；
- runner hard cap = 10.5 CNY；
- 实际新增费用 = 7.451754 CNY；
- 429/429新请求均生成receipt并完成；
- Qwen full-view用于zero-label ensemble/label-model研究，target GT仍只用于最终评价，不进入目标域适应过程。

本amendment不回写初始protocol hash；最终055结论必须同时引用初始protocol与本修订说明。
