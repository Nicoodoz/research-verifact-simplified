# 冻结评价与先后关系

本轮尚无R1新输出。本文件只登记将来的评价规则，不把计划当实测。

1. 校准集合固定143 ID。052一维G目标为裸log-score上的平均NLL＋0.01 theta²、边界[-6,6]；先拟合G，再加固定参考/校准比例的log-ratio。禁止在已经加prior的logits上重新换目标拟合，也不扫正则或类别权重。tie-break沿053的NS、NA、S顺序。
2. R1少量core无效时用真实有效校准交集，两模型同ID同步重拟合；交集比例重算、参考1378比例不变。没有完整三类监督或可靠分数则保留raw与缺口，不造分数。R1新参数在读取`evaluation_labels.jsonl`连接预测之前冻结。
3. 主面板原生比较先给Original、095 V4 raw、R1 raw共同raw有效分母；综合完整大表使用所有所列score方法共同有效分母，单列完整N/无效/缺失。不可把不同分母混入同表。主要表列方法、有效N、正确、PA/MCC/AC1/Macro-F1、三类recall、false-S/non-S；每个指标方向正确地标最佳，类别风险不靠总分掩盖。Precision/F1/S-FDR与混淆矩阵放附表。
4. R1同一回答离线计算raw、U0、旧V4 Frozen PriorG、R1 adapted PriorG、prior-only、fitted-G-only；raw与U0仅实际逐例一致才合并说明。另给小G/先验作用的标签差与转移，不因参数数值变化就宣称分类收益。
5. paired_compare及1000次患者bootstrap：R1 raw−Original、V4 raw−Original、R1 raw−V4 raw、adapted−raw、adapted−直接Frozen。列救回/伤害、错误支持增减、human/LLM、患者分布。按作者×GT纳入权重补充标准化结果；缺失机制不被抽样权重消除。
6. 主800与压力200互斥分报，600/100等备选按预检费用在正式发送前一次选择。压力面板不与主面板拼总体PA。选主600时使用其自己的分层配额和权重，不能沿用800权重。
7. V4桥接只作批次诊断，原095缓存包含其原无效并保持首次规则；桥接的好答案不得替换主表。Original-style可选接入未完成，不伪造结果或给作者reference＋T-S换名。
8. 三个结论分开：原生系统相对作者的位置；旧参数跨模型迁移；同配方重拟合是否有额外效用。若都未升级照实结项，不搜索到获胜。全部患者已有开发暴露，排除16校准患者不是新外部验证。
