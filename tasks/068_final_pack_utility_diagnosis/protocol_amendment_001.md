# 068 预检修订 001：识别字面量换行分隔符

首次 `prepare068.py` 在未调用 API 前生成了 `freeze.json`、`jobs.jsonl`、`mechanism_mapping.jsonl`。其段落完整性检查调用 067 的 `reference_blocks`，该函数只识别真实换行后的 `N. Date:`。067 final reference 在段落间实际含字面量反斜杠加 `n`，导致首次预检把 226 个 changed pack 的大多数误读为单段，错误地判为没有可比的“只重新呈现”对照。

原预检文件保留为 superseded 记录。修正仅针对 068 段落解析：同时识别真实换行与字面量 `\n` 后的 `N. Date:`，比较 passage 原文时将两类换行都归一化。重新冻结为 `freeze_002.json`、`jobs_002.jsonl`、`mechanism_mapping_002.jsonl`。新增请求尚未发送，样本、费用上限、决策标准均未改变。

这一格式差异本身属于呈现变化，不能把 067 效果直接归因于新增信息。
