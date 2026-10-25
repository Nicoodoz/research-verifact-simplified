# 094 历史差异与文献依据

本轮定向核查输入组装代码，未重新审计全仓。028/048/049/065中的independent、blind通常指不见GT或由另一调用处理，并不等于隐藏原claim所声称的答案。

|操作|最近旧实现|实际输入区别|本轮判断|
|---|---|---|---|
|逐要求取证、引用及全支持放行|028 common028.body/TRACE_INSTRUCTION|trace同时接收proposition与reference；目标取值可见，最后还有全支持条件|不复做其Gate；094不设全支持放行|
|要求/查询→检索→逐项核查|048 common048.audit_body调用039 common039.audit_body|payload明确含proposition、C48、additional_EHR；claim-only查询生成并非答案隔离取证|094固定C48、不扩检，仅Q取证去掉claim|
|关系注释交给Judge|049 build_screen_methods049.REL_SYS及verification_index|沿048已经看过claim的审核关系；对齐/反证条件均已试验|094保留可见V作为相近整理对照，不把关系表本身叫新机制|
|要求驱动证据构造|065 common065.composer_body|proposition、requirements、candidates均送composer；输出选择IDs，非盲问题作答|真实三臂23共同有效，focus/full增益有限；不是未执行，也未测094隔离|
|精确去重后补段|093|改变目标证据表示和内容，实际操作16/120|094完整C48不变；事前逐题核查操作覆盖，不重复packing|
|独立复核与分歧裁决|015 common015.build_body/verify015、016沿用分歧触发复核|evidence-only仍有proposition/reference，adjudication还可见candidate_judgments；屏蔽旧判断不等于屏蔽claim答案|094不输入旧Judge结论/reason，且Q额外去掉claim；016曾通信/预算停止，不能当完成全量方法阴性|

未在以上最接近可执行工件发现完全相同的“同问题/同C48/同取证模型，唯一差别是是否可见claim，再交同最终Judge”实测。此结论限于定向核对范围，不宣称所有旧文件都被审计。

QAGS（Wang、Cho、Lewis，ACL 2020）从生成文本构造问题，分别在源文档和生成文本上作答，比较答案一致性；其方法本来就区分源文档QA与生成文本QA。094不是问答事实核验首创，也不复刻它的抽取式模型或答案F1指标。[原论文§3–4](https://aclanthology.org/2020.acl-main.450.pdf)。

Chain-of-Verification（Dhuliawala等，Findings ACL 2024）§3.3区分joint、two-step、factored：two-step取证上下文不含初始回答，factored还隔离不同问题；§3.4再利用原回答与核查结果生成最终回答。094每条只问一个问题，屏蔽claim目标取值的思想直接承接这类上下文隔离，区别在临床固定C48、医生三分类GT、匹配V对照及既有PriorG兼容性。[原论文](https://aclanthology.org/2024.findings-acl.212.pdf)。不搬用其数据集成绩宣称本系统优势。

源代码/报告SHA见history_sources.json。论文仅作为方法来源，不作为本轮已运行基线。
