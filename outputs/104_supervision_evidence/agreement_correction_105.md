# 105接手时的104派生统计更正

原CSV一致数字段是字符串，旧`analyze104.py`直接与整数3比较，导致`annotation_and_teacher_association`的三医生一致数被误计为0。105从原human_verdicts.csv.gz逐条重建前三名医生投票，并核对原GT，得到：保留196条中92条三人一致；unresolved 78条中21条三人一致。其余分层与指纹见`agreement_correction_105.json`。

已修正分析器的类型比较。原冻结`supervision_summary.json`和`complete.json`保留；更正阅读件为`supervision_summary_corrected.json`。196条两臂、医生GT、原始回执、其他104结论与费用均不改变。
