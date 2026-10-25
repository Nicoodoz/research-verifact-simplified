# 034 冻结方案

只做现有预测的同ID连接与统一重评。

输入固定为：
- 002：R1-70B、100 sentence facts、valid-only的human/LLM claim发布预测；
- 033：40名development的full_predictions.csv，其中取U2和A_all40患者外预测。

要求：
- proposition_id严格一一对应；
- 原VeriFact必须覆盖034全部3675条，否则停止；
- 三方法使用相同GT、相同评价分母；
- 统一调用002的evaluate与paired_compare；
- 主指标为PA、MCC、AC1、false-S，并报告human/LLM和三类性能；
- 配对区间采用1000次患者cluster bootstrap；
- 不使用reserved40，不搜索参数，不新增模型调用。

A全40表示训练策略覆盖全部development，但034中的评价预测为033保存的患者外/LOPO版本，不是全40最终模型在训练患者上的直接成绩。
