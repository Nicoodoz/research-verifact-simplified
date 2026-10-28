# 104私有盲审台账接口

首轮只读 `.local_models/104_supervision_evidence/blind_cases.jsonl`（288，完整原reference），不要打开gt_key、teachers、doctor_annotations或包含GT的资产行。正文可用 `python -B tasks/104_supervision_evidence/review_io104.py <review_index>` 查看；必须看到END标记并完整阅读，输出截断则补读原文剩余部分后再判断。不能用词法窗口代替完整reference。

初始分工计划为三名首审者各96（按index%3分片）。实际执行在GT连接前按工程工作量重新分工，最终为root 24、semantic_b 132、semantic_c 132；逐ID以私有`assignment.json`及公开`blind_review_freeze.json`指纹为准，不按旧mod3计划推断实际作者。样本288、首判顺序与科学口径不变。首审是机器辅助，非医生gold或独立临床审计。

每条一行JSON，写各自 `.local_models/104_supervision_evidence/review_root.jsonl`、`review_b.jsonl`、`review_c.jsonl`，不要覆盖其他人。字段：

```json
{"review_index":1,"id":"...","reviewer":"root","full_reference_read":true,"claim_slots":{"subject":"...","event":"...","time":"...","qualifiers":"..."},"independent_verdict":"Supported","certainty":"high","evidence_quotes":["exact short quote"],"relation":"English concise 2–4 sentences explaining actual fact correspondence; target 50–100 words, accuracy first.","issue_tags":[],"na_anchor":"not_applicable","review_stage":"blind_v1"}
```

independent_verdict只允许Supported、Not Supported、Not Addressed或Unclear。certainty取high/moderate/low；无法合理解决保留Unclear/low，不凑合格。evidence_quotes是当前reference中的真实短句（可跨多个段分别引句），构建时程序定位并保存start/end/SHA/source元数据；若引句多次出现需复核所有可能位置而非任意指定。NA没有有意义相关anchor时允许空列表，na_anchor=none；有相关主题但目标事实未涉及为related_context；其他为not_applicable。

先独立作判断，不编造对齐GT的理由。命题涉及但只部分支持通常NS；命题的特定事实并未涉及通常NA；参考文本里未找到不是自动NS或NA。保留对象、事件、时间、程度、因果、治疗身份及患者身份区别。临床缩写可合理读解，但无法解释需标歧义。复合命题不能只检查其中一部分。

可用简短笔记说明歧义，但不得写“医生GT是...”或声称缺乏记录证明整个EHR不存在。50–100词为目标，不写长思维链，不添关键词规则制造通过。issue_tags可如subject_binding/event_binding/time_binding/degree_qualifier/causality/partial_support/related_topic_only/reference_insufficient/contradictory_reference/ambiguous_terminology等，用于事后统计，不能替代实际审查。

审查正文和理由全部私有；公开报告只保留聚合数量、hash和抽象关系例证。每完成约12条报告一次进度；独立首审封存后才join GT/教师并做理由修订与独立复核。
