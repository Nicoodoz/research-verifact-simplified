# 033 当前状态

2026-09-20：快速独立审计完成，**PASS，可冻结／结项**。

本任务是新的Gate训练subset研究；旧033 reserved准备已撤回，改名为withdrawn_reserved_preparation_20260920存档，没有进入本轮输入。

- 完整复用030的141轮、1452固定集合、4356最终模型；没有重新执行原030大规模训练。
- 历史和定向搜索共同第一名：A3=`31135,59840,9030`；D5=`27036,27823,59250,59840,93640`。23个定向邻居、36个新最终拟合未改进第一名。
- 12人选择隔离核查：A3较A全训练LOPO +4正确、+1 false-S，同风险−1.20R；D5−1正确、−4 false-S，同风险+0.40R但区间跨0，rescue保留76.1%。没有稳定更优subset。
- 推荐未来Gate训练策略保留A＋全部development40人；A3小幅工作点收益保留作探索备选，不宣称3人为最佳人数。推荐不是reserved最终成绩。
- 总178个新最终模型（含定向36及必要LOPO/最终基线），4828个内层拟合状态；48422项执行者只读核验通过。
- 0 API、0费用、不使用reserved40、不改历史/.gitignore/主环境；用户本轮授权通过后提交推送，不自动新实验。

[唯一中文主报告](report.md) · [训练subset排名](training_subset_ranking.csv) · [推荐训练名单](recommendation_001/training_patients.csv) · [交审](audit_handoff.md)。

[独立审计](../../reviews/033_gate_training_subset.md)：包含verify入口会更新进度元信息的说明；科学结果未改。旧撤回准备仅保留本地，不纳入本次提交。
