# 091 审计交接

起始HEAD `70be6428fb0d1851ed9414a54cee2b30928e144e`。新增目录tasks/outputs 091；旧036、078—090和085正式结果原位保持。新增收费API0次、¥0/20。未使用reserved开发或选参，036仅引用正式报告/方法汇总。

首先读report.md、manuscript_zh.md和evidence_map.md，再核对B_diagnosis.json及B_case_paths.jsonl。重点检查自然167的raw9救回/2伤害如何变最终4/2；完整176额外fallback伤害不可混入有效评分解释。压力65最终净0，完整66净+1涉及invalid/fallback，不能归为有效核心收益。检查prior-only的138与PriorG137是否只由已有G边界产生，并确认没有据此选新阈值。

排序分析使用类对log-ratio，不是含多类竞争的任意margin；固定类偏置不改变该AUC。患者留一和时间四块是事后集中性描述，不是新的患者外确认或随机批次实验。B_repeat090按实际UTC最早回执选取、必须body SHA相同，重复引用同回执不增加样本；P90无同体重复。082的24条没有真NS，不能把F4最终0翻转外推到少数类。

C_material_inventory来自不使用旧分数/标签的字段白名单盘点，没有连接C GT。原型数值匹配不处理主体/时间/否定，是可行性停止理由之一；不是充分性正确率测试。软件例子为合成装置文本，不能称新医生GT。没有C分类预测或未知费用，不应填写C的“0收益”或等效结论。

自检采用单独混淆矩阵算式核对49个配置表；7个单测覆盖关键来源与动作边界。大量check计数是逐记录/字段守恒和扫描，不代表大量独立研究测试。独立外部审计未执行。安全复核命令见任务README，不要运行历史runner或新实验。

交付清单包含文件SHA与源指纹。私有盲池在outputs/replays/091_integrated_evidence_decision_study/C_blind_pool.jsonl，仅供合法环境读取；公开版不含claim/reference或新原生回执。用户已授权完成后直接commit/push；这不授权下一研究任务。
