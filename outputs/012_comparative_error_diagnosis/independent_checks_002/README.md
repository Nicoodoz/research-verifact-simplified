# 012 否定词边界计数的补充独立核查

独立从010冻结的650条C48实际reference解析7,861个入选块，逐块与同患者、同note原EHR字符范围及009索引文本核对，再检查段首之前是否紧邻大小写不敏感的完整词`No|not|without|denies`（中间只允许空白）。没有导入012的筛选实现。

重建结果：**40次、40个不同claim、11个不同原始切点**。切点按`(subject_id, note_id, start字符位置)`定义，重复note不跨ID合并。独立重建候选集合与`pipeline_001/boundary_candidates.json`一致。明细及原文边界上下文见`occurrences.json`，分切点复用次数见`result.json`。

这只是机械边界候选，不是40个医学错误、40次否定理解错误或总体因果归因发生率。多数命题复用同一切点；note375697的12111切点被17条claim使用。N036/N047的最终reference同时保留了以“No”结束的前块和以“nausea”开始的后块，因此还不能将全部候选概括为“否定词在最终reference完全消失”。本次不扩大语义深读，也不评价这些病例是否临床正确。

代码与来源指纹分别是`check_boundaries.py`、`source_hashes.json`。执行命令：

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B outputs/012_comparative_error_diagnosis/independent_checks_002/check_boundaries.py
```

无API调用、无新患者、无历史结果修改。本记录是有界独立复核，不是整个012的独立审计结论。
