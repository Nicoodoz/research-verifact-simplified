# 114 matched_refresh 当前状态

COMPLETE_STOP_CURRENT_RECIPE

114 matched_refresh已完成原底座单候选50步、392次呈现（351不同ID）和500条全有效首次预测。自然MCC .5032→.5029、PA79.75%→79.00%、false-S12→8/79；压力MCC .3123→.3410、PA58%→61%、false-S16→16/100。自然/压力分别误伤10/9条正确NA且无NA救回，未通过事前NA保护条件；停止当前配方扩大，107仍为唯一维护的普通微调基线。GPU估算¥1.4252/3，API0，完整状态与回执已回传。按用户政策未关机，不自动115或默认升级。

[报告](../../outputs/114_matched_refresh/final_report.md) · [比较](../../outputs/114_matched_refresh/comparison.json) · [协议](protocol.md) · [实时进度](../../outputs/114_matched_refresh/实时进度.md)。

GPU及回传工作已结束，无需重复运行。完整checkpoint、原始预测和日志在`.local_models/114_matched_refresh/evidence/`。18:13核实实例仍开机、GPU无计算进程；未发shutdown，继续开机会计费。

本轮没有新的提交/推送指令，保留113、114及用户已有本地改动；完整main b3bac162、精简main f533f929不冒充当前成果已推送。
