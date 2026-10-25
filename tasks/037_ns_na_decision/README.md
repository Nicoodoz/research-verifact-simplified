# 037：固定Supported集合的NS/NA决策研究

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/037_ns_na_decision/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

用户明确授权的新探索性任务；036“不自动037”为历史边界。本任务不使用036 reserved做新预测或选择。
目标：保留Std_V概率与Supported集合，比较固定V/M切换、NS/NA单阈值及四维Logistic能否恢复NS识别。
数据：40名development、3675条，沿035四折；旧R1的879条作为评分条件敏感性，不是新患者。

## 结果
V/M切换：3101/3675，PA84.38%、MCC0.5506、NS召回39.06%、NA召回56.91%、false-S237。
原V：3081/3675，NS召回8.08%、NA召回71.75%。修复以92条NS救回换72条NA误伤。
Logistic与固定切换在两个数据视图逐条同标签，未提供额外价值；单阈值主队列少1正确。
建议保留简单切换作为探索分析，不将其称为新最强分类器或036最终冻结方法。

## 环境与重放
从仓库根目录使用既定启动器；输出目录/验证文件必须是新路径：
```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/037_ns_na_decision/test037.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/037_ns_na_decision/run037.py --output outputs/037_ns_na_decision/replay_001
pwsh -NoProfile -File scripts/run_research.ps1 tasks/037_ns_na_decision/verify037.py --run outputs/037_ns_na_decision/run_001 --output outputs/037_ns_na_decision/verification_002.json
```

主报告：outputs/037_ns_na_decision/report.md。
协议：protocol.md；正式运行：run_001；参数/ID/内层阈值账本：run_001/fits。
执行者10项合成测试及10项科学核验通过，独立审计待进行。0 API，不自动提交、推送或038。
