# 090 夜间构造修复与四臂补验

本次明确授权恢复089后的固定示例研究，40元原价总上限、构造≤4元。085及本地R1服务暂停。原样保留085/089，不自动091。

入口：[协议](protocol.md) · [最终报告](../../outputs/090_demo_constructor_repair_validation/report.md) · [明早简报](../../outputs/090_demo_constructor_repair_validation/morning_brief.md)。

主交付推送后完成的零API材料：[084—090地图](../../outputs/090_demo_constructor_repair_validation/results_map_084_090.md) · [论文草稿](../../outputs/090_demo_constructor_repair_validation/paper_draft.md)。

`engineering090.py`对088/089全部旧回执作零API回归及固定8项真实检查器功能测试；`construct090.py`第一工程版简化P/Q接口；`repair_construction_v2.py`第二且最后一版只修不同来源事实被错误替代的约束。原构造回答复用，不以目标效果重采样。`prepare090.py`冻结双面板；`api090.py main`只恢复未成功请求，成功不重发。

新临床原文、请求、完整模型回执和来源引文仅在现有已忽略目录`outputs/replays/090_demo_constructor_repair_validation/`。公开版只有ID/哈希、标签/分数/usage、指标与脱敏报告，不改.gitignore，不将旧公开原文作为继续扩散依据。源码引用旧材料用于本地合法数据复核。

零API复核：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/test090.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/test_recovery090.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/verify090.py
```

任务执行中断恢复（仍须遵守累计40元，不能删除账本重置）：先`api090.py status`，确认没有仍运行的旧进程，再用`api090.py main`续未成功请求。run.lock若残留，先核实进程已结束及原始未知回执，不能盲删。构造/prepare/analysis/export脚本独占写入，不覆盖冻结工件。完成后不作为自动续跑入口。

评价复用公共evaluate/paired_compare，另有独立算式核对混淆矩阵指标；执行者自检不是独立审计。若私有原文工件缺失，应在合法数据环境恢复，不凭公开摘要重造回执或私自追加收费复跑。
