# 教学池来源范围说明

`example_pool.jsonl`中的新增例保留其来源工件的**完整已存档参考文本**，未从中抽短片段；首批071的两条S例沿用其已审核的完整直接证据块。新增例`c92377ee`来自`outputs/044_incremental_evidence_recovery/planning_001/train_cases.jsonl`的`base`字段，即044的原C48 base包；它不是在072重新检索或重新裁剪的“053 final reference”。冻结池统一写作`selection=full_final_reference`的含义仅为“使用来源文件中的完整参考字段”，不能由此推断各历史任务检索链路等价。`source_file`、`full_final_reference_sha256`和冻结请求体可逐条复核。此说明不修改首次API前冻结的示例文本、请求或医生标签。
