# 092 审计交接（随真实结果更新）

**最终更新（2026-09-27）：** 用户完成AutoDL训练后授权收尾；十组训练、9065双臂OOF、唯一融合及原文部署实测已完成。下方暂停段落是历史记录，不能覆盖本段。最终报告/新论文稿/metrics/paired/fusion_results/final_costs/selfcheck/final_selfcheck构成当前交审入口；本地暂停工件保留在local_pause_archive。云端环境与原Windows冻结记录明确分开，云端命令日志未提供。自检不是独立审计。

**2026-09-27用户暂停：** 仅Frozen fold0完成，Fine-tuned fold0在第5轮中途保存恢复检查点，其余折未运行。以下是后续审计计划，不代表已经完成全量评价。暂停检查见pause_selfcheck.json；全量oof_predictions.jsonl和最终selfcheck.json尚不存在。有效训练冻结为training_freeze_v3.json，旧版本保留。

本轮是执行者研究任务，不自动标为独立审计。重点核查以下科学不变量：

- 032历史encoder确实冻结；092不是旧32维残差头的改名。核查模型参数requires_grad、优化器组和最终权重/表示变化。
- 9065个有效atomic ID均有原医生GT及原作者预测；不混入sentence或30个invalid atomic。用户092授权全部标签使用是新CV范围，036历史角色/成果未改。
- 每个OOF病例患者不在该模型的梯度训练及validation选择患者中。内层选择未读取outer性能；最终权重和最佳epoch可追溯。
- 两臂输入相同，全部C48 token覆盖；full1024维、不读旧分数。新增1817条本地C48与7248旧缓存分层，不能声称API逐字等价。
- Frozen与Fine-tuned头、loss、种子、监督预算一致；缓存只是固定底层计算，不把final-layer adapter变化冒充所有24层更新。
- 全量主指标使用公共evaluate/paired_compare。概率指标为本地分类softmax，不声称临床校准；false-S/真实non-S与predicted-S假发现率分母分开。
- B/F4采用固定来源优先级且核对reference。原fallback原样保留；历史缓存混合选样不冒充全量自然总体；090压力/自然另表。
- 一次种子的五折不是五次独立实验；患者bootstrap固定训练后预测，不覆盖重训或选择不确定性。
- 可选融合若启动，必须所有参与其训练/表示/选择的标签都排除outer患者，不能直接用别的fold的OOF特征导致间接泄漏。
- Git只含代码、ID、标签/预测、源SHA和汇总；原文、token IDs、激活、checkpoint、私有回执不提交；不改.gitignore、默认系统或历史输出。

复现命令见任务README。公开`training_freeze.json`、`folds.json`、`bags.jsonl`、各fold完整标记、`oof_predictions.jsonl`及`selfcheck.json`形成主要核对链。未产生的工件不代表已完成；正式报告以实际结果为准。
