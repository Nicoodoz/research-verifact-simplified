# 必要相关工作与价格核对

查询日期2026-09-26；以下根据原论文官方条目/摘要作范围核对，不声称完成全文逐节复现。

|原论文|与本轮的联系|不可直接外推|
|---|---|---|
|[Min et al., EMNLP 2022, Rethinking the Role of Demonstrations](https://aclanthology.org/2022.emnlp-main.759/)|在其分类/多选设置中，随机替换示例标签常只有小影响；输入分布、标签空间与格式也可能提供作用。支持分开控制示例信息。|不是本任务F4证据无用的证明；本轮不重复标签置换。|
|[Wei et al., 2023, Larger Language Models Do In-Context Learning Differently](https://arxiv.org/abs/2303.03846)|模型规模、语义先验和标签映射学习影响错误/无语义标签下的表现。|不能把某一模型族的标签实验直接移植到本DeepSeek临床证据置换。|
|[Hashimoto et al., NAACL 2024, Take One Step at a Time to Know Incremental Utility of Demonstration](https://aclanthology.org/2024.naacl-long.221/)|比较有无示例的增量效用，强调效用定义及下游任务差异。|087不训练选择器，不主张增量效用思想首创；自报label_scores也不是其真实输出概率。|

[阿里云deepseek-v4-flash官方页](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)的独立`deepseek-v4-flash-0731`快照节，列北京忙时输入3/输出9元每百万token，闲时1.5/4.5、缓存输入另价。本轮使用忙时非缓存原价计全量usage；不混用页面顶部滚动别名的其他价格。实际端点本地核验为既有北京workspace `/compatible-mode/v1`，不输出凭据。
