# 121 nearest_memory

固定107的 verdict_prefix 表示做余弦kNN，32人2945训练、8人730验证。内部验证选择 k=31、uniform；6个配置完整指标见 results.json。无新神经网络训练/GPU/API。

|范围|方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA净救回|
|---|---|---:|---:|---:|---:|---:|
|160 natural (128)|label_only107|0.4165|75.00%|96|5/25|—|
|160 natural (128)|candidate|0.5072|85.16%|109|10/25|16/-1/-2|
|160 pressure (32)|label_only107|0.3191|59.38%|19|5/32|—|
|160 pressure (32)|candidate|0.3375|53.12%|17|10/32|0/-2/0|

在160范围未通过事先冻结的综合/风险继续规则，停止当前kNN配方；未继续扩大或搜索。

最初160条新增false-S 10次、避免0次。自然集准确率提高不能抵消这些新增错误放行；全部类别得失照实保留。

107祖先已见原40人的196条，内部验证不是完全无祖先暴露；选型20人亦有历史研究暴露。训练记忆只使用原GT，患者ID不作为特征。各类救回/误伤、混淆矩阵和全部验证配置保留在JSON。

CPU近邻时间不等于完整部署速度：新输入仍需107的完整prefill。新增GPU/API费用均为0。

方法参照：[kNN Prompting (ICLR 2023)](https://arxiv.org/abs/2303.13824)；本试验使用隐藏表示余弦，不声称复现其完整方法。反证：[Great Memory, Shallow Reasoning (NAACL 2025)](https://aclanthology.org/2025.naacl-short.40/)说明近邻记忆并不保证多事实推理。
