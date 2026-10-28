# 107 support_aux

训练期S/non-S辅助监督的固定两臂研究。当前入口见[CURRENT](CURRENT.md)，科学设计见[protocol](protocol.md)，实际状态与CPU结果见[准备报告](../../outputs/107_support_aux/preparation_report.md)。

CPU阶段：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/107_support_aux/prepare107.py`核对原数据；tokenizer与tiny torch CPU测试复用本地032环境。`run107.py --help`与默认预检不初始化GPU。私有GPU包不含基础权重或凭据，不可发布；远端仍须核对实际权重、环境与计费。
