# 036 当前费用入口

正式入口为[accounting_002](accounting_002/summary.json)。accounting_001费用和原始账本始终正确，但rerank token统计列未读取供应商meta而错误显示0；002逐条从4228份BGE回执重建输入token并核对费用。原001/回执不改，总费用和预测/评价完全不变。

零API复查：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/correct_accounting036.py --verify`。
