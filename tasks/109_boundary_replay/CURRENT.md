# 109当前状态

COMPLETE_NEGATIVE_STOP_CURRENT_RECIPE

109 boundary_replay已按新租卡授权完成：107 label_only完整状态续训，527条真实预测后固定选出192条/24步，500条评价全有效。相对107自然MCC0.5032→0.3733、PA79.75%→72%、false-S12→11/79；压力MCC0.3123→−0.1091、PA58%→38%、false-S16→16/100。主要是NA→NS严重交换（候选仅预测1条NA），停止当前配方，不补普通回放或启动110。完整模型/optimizer与原始结果已回传；由用户关机，停费已确认，API0。标签微调既有收益及默认系统保留。

实际训练192条S80/NS48/NA64，来自原训练40人，与评价20人隔离。三组各64条：真实错误、当前正确近S、当前正确保留；64真错含35个false-S。续训global step50→74，原loss、BF16、完整输入不变，最终500条均有效。当前结果是真实分类阴性，不是CPU测试、数据配额不足或格式失败。

NA自然正确40→1、压力41→0；NS召回改善不能抵消NA塌缩。普通回放对照、追加epoch/种子/阈值/池扩展均未运行，不启动110，不升级默认。仍不能把失败唯一归因于困难选样或单纯追加训练。

最终适配器和完整optimizer/scheduler/RNG在.local_models/109_boundary_replay/gpu_evidence/results/train/checkpoint_a/，519867504 bytes且回传核验通过；全部原始预测/训练清单/日志在同级results。约11:29通知用户关机；平台停费已由用户确认，GPU租金当前估算¥1.8960，API0。

无卡准备双仓库已推送：完整c944c304、精简88cf24af。用户现已明确要求推送本次GPU正式结果与分析，最终双仓库提交及远端核验以本次交付为准。原无卡准备报告和自检保留其形成时范围。

[最终报告](../../outputs/109_boundary_replay/final_report.md) · [完整指标](../../outputs/109_boundary_replay/comparison.json) · [执行自检](../../outputs/109_boundary_replay/execution_selfcheck.json) · [费用](../../outputs/109_boundary_replay/execution_cost.json)
