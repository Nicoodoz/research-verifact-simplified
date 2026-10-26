# 100错误转移与判定说明

确认自然共同189条，L24比O净多对1条，却使MCC从0.4789降到0.4584、错误支持从4/37增至6/37。正确数变化按GT为{'Supported': 4, 'Not Supported': -1, 'Not Addressed': -2}：Supported改善掩盖了NS/NA损失，不能用PA单列包装为成功。

开发L−O ΔMCC为+0.1208，独立患者确认变为-0.0205。方法、24K、规模和判据均未重调，未为延续开发阳性追加样本或候选。

确认同长度S/L实质相同与标签变化：{'natural': {'frozen_N': 192, 'same_S_L_body': 76, 'different_S_L_body': 116, 'valid_S_L': 191, 'S_L_label_difference': 11, 'label_differences_by_GT': {'Supported': 6, 'Not Supported': 3, 'Not Addressed': 2}}, 'pressure': {'frozen_N': 32, 'same_S_L_body': 14, 'different_S_L_body': 18, 'valid_S_L': 32, 'S_L_label_difference': 3, 'label_differences_by_GT': {'Not Supported': 2, 'Not Addressed': 1}}}。L没有超过S24的MCC或实用门槛，完整note机制未成立；相对更便宜C也没有实用优势。普通BM25、完整note检索和长度配平本来就不是新算法，本轮最多检验其任务适配，不能改名包装。

重复共同15/16，翻转{'L24': 0, 'O': 0, 'S24': 1}，第二次L−O ΔMCC=-0.1307。主实用路线均未通过，没有可声称稳定的核心优势；confirmation_decision.json中的stability_pass字段不能单独解读为总体稳定性通过。完整首/重复表保留原样；最终“失败停止”不变。

压力的false-S减少不抵消自然MCC/类别损失。原GT、原始回执和首次答案未更改，没有新收费调用。逐GT转移、救回/伤害、患者输赢与费用见error_transfer_analysis.json。
