# 033 Gate训练患者subset研究

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/033_gate_training_subset/report.md)。 独立结论查[审计末尾](../../reviews/033_gate_training_subset.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

033已通过[快速独立审计](../../reviews/033_gate_training_subset.md)，下方“待独立审计”仅是形成时快照。

## 原任务阶段说明（历史）

[报告](../../outputs/033_gate_training_subset/report.md) · [冻结协议](protocol.md) · [当前状态](../../outputs/033_gate_training_subset/CURRENT_STATUS.md) · [交审](../../outputs/033_gate_training_subset/audit_handoff.md)。执行及自检完成，待独立审计。

固定029 A/B/D特征及Logistic规则；完整复用030，新增搜索仅A/D一次23集合。使用隔离research-verifact-029，不安装或修改主环境。所有Python入口导入后禁网，无API客户端。

安全离线核验（必须用新目录名，0拟合、0 API）：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/033_gate_training_subset/verify033.py --output verification_audit_001
```

阶段顺序为prepare033→bank033→association033→search033→evaluate033→supplement033；各正式阶段拒绝覆盖既有目录。原执行已完成，不要重新运行这些入口覆盖或重做搜索。bank复用模型，search只跑冻结邻居，evaluate完成必要OOF/全训练模型，不能据核查结果返回search。

plot033 --output <new-folder>可从机器结果重画；正式图为figures_002，001保留初版文字布局。推荐模型仅是后续训练策略建议，不自动触发任何reserved实验或提交推送。
