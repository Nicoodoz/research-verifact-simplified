# 104资产清单字段解释

`asset_inventory512.jsonl`保留原512条的程序化清单，正文在私有同名文件；本说明及三个补充表不改变原inventory_freeze或任何103输入/标签。

- `round1_num_raters_agree`是初轮三名医生的标签一致数：3为三人一致，2为两人一致，0为三种标签各一票，不是没有医生标注。它不是最终GT置信概率。
- 512条初轮投票及最终human_gt均无缺失。480条以初轮多数为最终GT；32条初轮三种标签不同，经后续裁定形成原human_gt。480条adjudicated_verdict为空是未触发该流程，不能算最终标签缺失。
- `doctor_vote_counts`原清单累计非空的1—5轮投票，不能当作初轮一致数；明确拆分的初轮票与最终GT来源见`annotation_inventory512.jsonl`和`annotation_summary.json`。
- 教师`same_reference`严格要求命题ID、claim、reference ID及实际正文SHA相同；教师预测=GT只是理由候选条件。其他reference的解释不进入复用候选。
- `teacher_quote_mechanical.jsonl`/`teacher_quote_summary.json`仅对正确标签候选理由中的显式双引号片段做精确定位，保存所有重复位置的数量；没有引号不等于理由错误，有来源位置也不认证关系、对象、时间或标签正确。完整reason/reasoning字段继续私有。
- 原reference通常发布显示编号、日期、类别及描述，未发布原始note ID时不得把显示编号冒充note ID；构建配对包时保留null和缺失说明。
- `duplicate_summary.json`区分同claim不同GT与近重复候选。词集合近似只用于盘点，不能当成临床关系判断或自动删除理由。
