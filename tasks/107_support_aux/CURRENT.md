# 107当前入口

107两臂GPU训练与1000条首次评价完成：label_only/support_aux均在本次5090从原9B新训196×2轮/50步，数据/初始化/顺序/原105主loss不变，候选仅增加训练期S/non-S BCE权重1；batch2两臂同250组，推理不用辅助头。543文件已回传SHA核验，含两臂最终完整optimizer、适配器、辅助头及原始回执。用户已确认关机，待CPU离线统计；API0，GPU费用按2.88元/小时从20:40累计，精确账单待核。尚无107分类结论；不启108/扩大/升级默认。

[当前报告](../../outputs/107_support_aux/execution_completion.md) · [协议](protocol.md) · [执行与关机](GPU_HANDOFF.md)。
