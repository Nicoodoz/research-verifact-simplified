# 自主研究周期1：阶段结果

107 label_only仍是主基线。以下均为原20名患者的开发筛查，原医生GT保留；后40人尚未用于选型或确认。各候选首次回执保留，未按结果重发。

|候选/面板|配置|MCC|PA|正确数/有效数|false-S/有效非S|有效/计划|
|---|---|---:|---:|---:|---:|---:|
|joint_path_pilot/natural|107 label_only|0.4078|71.67%|86/120|4/24|120/120|
|joint_path_pilot/natural|joint_path|0.3962|61.67%|74/120|0/24|120/120|
|joint_path_pilot/natural|作者历史R1|0.4190|77.50%|93/120|6/24|120/120|
|joint_path_pilot/pressure|107 label_only|0.3069|58.33%|35/60|7/60|60/60|
|joint_path_pilot/pressure|joint_path|0.3710|65.00%|39/60|3/60|60/60|
|joint_path_pilot/pressure|作者历史R1|0.2669|53.33%|32/60|14/60|60/60|
|claim_repeat_pilot/natural|107 label_only|0.4078|71.67%|86/120|4/24|120/120|
|claim_repeat_pilot/natural|claim_repeat|0.4735|76.67%|92/120|4/24|120/120|
|claim_repeat_pilot/natural|作者历史R1|0.4190|77.50%|93/120|6/24|120/120|
|claim_repeat_pilot/pressure|107 label_only|0.3069|58.33%|35/60|7/60|60/60|
|claim_repeat_pilot/pressure|claim_repeat|0.2945|58.33%|35/60|7/60|60/60|
|claim_repeat_pilot/pressure|作者历史R1|0.2669|53.33%|32/60|14/60|60/60|
|claim_repeat_500_missing/natural|107 label_only|0.5032|79.75%|319/400|12/79|400/400|
|claim_repeat_500_missing/natural|claim_repeat|0.5232|80.25%|321/400|12/79|400/400|
|claim_repeat_500_missing/natural|作者历史R1|0.4319|81.00%|324/400|28/79|400/400|
|claim_repeat_500_missing/pressure|107 label_only|0.3123|58.00%|58/100|16/100|100/100|
|claim_repeat_500_missing/pressure|claim_repeat|0.3219|58.00%|58/100|17/100|100/100|
|claim_repeat_500_missing/pressure|作者历史R1|0.1572|44.00%|44/100|30/100|100/100|

## 去留与解释

- `joint_path_pilot`：停止扩大；降低8次错误放行，但自然集误伤14条原正确S，净少12条正确。
  - natural：Supported救回0、误伤14；Not Supported救回2、误伤0；Not Addressed救回0、误伤0；新增false-S 0、避免4。
  - pressure：Supported救回0、误伤0；Not Supported救回7、误伤2；Not Addressed救回0、误伤1；新增false-S 0、避免4。
- `claim_repeat_pilot`：自然120净多6条正确、MCC+0.0658，false-S不变；压力净正确及false-S不变，继续补齐旧500。
  - natural：Supported救回6、误伤1；Not Supported救回0、误伤0；Not Addressed救回1、误伤0；新增false-S 0、避免0。
  - pressure：Supported救回0、误伤0；Not Supported救回2、误伤1；Not Addressed救回0、误伤1；新增false-S 1、避免1。
- `claim_repeat_500_missing`：自然400 MCC+0.01997、正确+2、false-S不变，S净-2/NS+2/NA+2；压力正确不变、false-S+1。有限信号，继续补齐1817，不宣称已成功。
  - natural：Supported救回6、误伤8；Not Supported救回2、误伤0；Not Addressed救回4、误伤2；新增false-S 1、避免1。
  - pressure：Supported救回0、误伤0；Not Supported救回2、误伤3；Not Addressed救回1、误伤0；新增false-S 2、避免1。

## 方法与代价

`joint_path`复用115最终适配器，枚举三个完整JSON+EOS路径并按总条件logP决策；每例三次完整前向。它联合验证115目标与路径决策，不能用仅比115原greedy好来宣布超过107。

与115原greedy有回执交集的70条中，自然35条正确24→22，压力35条21→22，正确S救回0、额外误伤1。该描述性交集没有支持“改用完整路径即可挽救115”的解释，也不能外推为全部样本的机制证明。

`claim_repeat`复用107，在完整reference之外的消息末端重述同一待核验命题；未增添EHR事实、GT、其他模型答案或逐例规则。

对其自然面板6条S救回及1条S误伤做了定向原文检查：5条救回有较明确可见依据，1条缺关键时间段，误伤例也有可见支持。3条有依据救回来自同一患者。这不是随机病例审查，不能证明模型使用了对应证据，或排除更偏S；缺证例仍保留医生原GT。临床正文与逐例笔记仅在私有目录。

`single_token_768`是待验证的完整判别配方：原9B、768条真实训练命题、32名梯度患者，另8名患者128条只用于选checkpoint。原临床定义与完整输入保留，A/B/C三行固定词表投影作唯一三类CE，96步；不把它当作纯组件消融或新的原创算法。

三类完整指标、混淆矩阵、逐例配对变化与患者方向保存在各候选JSON。当前粗筛不例行bootstrap；有值得保留的较大开发收益后再补必要稳定性分析。作者R1只作历史同ID参照。

周期起点2026-10-29 19:47:16（北京时间），截止2026-10-30 07:47:16；本报告生成时GPU墙钟估算¥1.074/20、API ¥0/20。估算包含等待和回传，不是平台精确账单。

状态：ACTIVE；当前任务`claim_repeat_1817_missing`；最佳`107_label_only`。不自动关机，实例继续开机会继续计费。

依据：[周期备忘](../../tasks/116_research_cycle/memo.md)、[预写粗筛规则](../../tasks/116_research_cycle/screen_rules.json)、[单token配置](../../tasks/116_research_cycle/single_token_config.json)。
