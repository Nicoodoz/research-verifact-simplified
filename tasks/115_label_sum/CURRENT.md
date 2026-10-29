# 115 label_sum 当前状态

COMPLETE_STOP_CURRENT_RECIPE

115 label_sum已完成原底座单候选50步/392次呈现和500条首次评价，原196数据、prompt/reference/接口不变，仅值段CE改为sum/(360/196)，107旧500全部复用。自然MCC 0.5032→0.3912、PA79.75%→59.50%、false-S12→1/79；压力MCC 0.3123→0.3205、PA58.00%→64.00%、false-S16→4/100。115未形成通过保护条件的综合增量，停止当前label_sum配方，保留107主基线。 GPU估算¥1.5455/3，API0，完整状态和原始回执回传。用户新授权本轮双仓库推送并补归档113/114；未自动关机，不启动116或默认升级。

[报告](../../outputs/115_label_sum/final_report.md) · [比较](../../outputs/115_label_sum/comparison.json) · [协议](protocol.md) · [实时进度](../../outputs/115_label_sum/实时进度.md)。GPU工作及回传已结束，无需重复启动。私有完整状态及回执在`.local_models/115_label_sum/evidence/`。

本轮用户已明确授权双仓库正常提交推送，并补归档113/114；实际成功以远端main核验及最终交付为准。[归档范围](../../outputs/115_label_sum/publication_scope.md)解释历史未推送描述。当前不自动关机，继续留机仍计费；不自动116或升级默认。
