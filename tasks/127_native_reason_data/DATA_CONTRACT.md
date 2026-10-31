# 127 原生reason监督数据合同

只读取106原40名训练患者的3675条池，沿用117所继承的32训练／8内部验证患者划分；不读取选型20或确认40的临床原文。原医生GT、claim/reference字符串UTF-8字节保留。构建脚本不自动生成临床reason，本阶段不新增9B推理、GPU训练或收费API调用。

`127_optional_reason_v1`是独立新模板：104的任务与三类定义原样保留，仅输出说明改为verdict必填、reason可选；reason若出现须1–3句，依据当前reference，并明确NA不等于患者没有该事实。两个目标使用同一输入模板：label_only仅verdict，verdict_reason始终verdict与reason。旧104/105/120函数与原生20例reason必填诊断不改。

逐ID记录由当前Codex及子代理在实际完整reference审读后AI辅助生成与复核，不是外部医师认证；程序本身不生成reason。字段为`reason_sentences`（1–3句）、`ai_assisted=true`（本批不得False）、`evidence_sources`、`review`。程序不会把旧evidence/relation字段拼入答案，也不会将草稿自动批准。`review.status=approved`、具名reviewer、verdict_consistent与input_grounded确认是入配对的必要条件；NA另须na_not_absence_checked，作者历史预测与GT不一致另须teacher_disagreement_reviewed。review还须以complete_sentences=true及sentence_count显式声明句数，程序只核对声明与列表长度，不冒充句法检测。未解决的问题放入review.unresolved_issues（如ambiguous、unsupported_modifier）。这些是AI辅助审核记录，不是新医生GT。

证据元数据支持实际reference字符跨度（kind=reference_span，start/end/quote，逐字核验）或整份输入审读（kind=whole_reference，reference_sha256、fully_read=true、review_record）。后者必须有完整审读记录，不能仅用关键词未命中。1–3句以审核提供的句子列表计数；程序不冒充医学句法或证据判断。

`prepare127.py --annotations <审核jsonl> --out <新私有目录>`完整保留all_label_only及独立issue_ledger；只有无未解决问题的可靠子集导出两份同ID、同序配对文件。ledger分别记录not_reviewed（待审，不等于被语义排除）、reviewed_unresolved（已审仍有问题）和approved。needs_review默认属于待审；status=reviewed_unresolved、review_completed=true或primary_full_reference_read=true表示已经审读，因此仍有问题时记为reviewed_unresolved。没有reason时允许配对N=0，不凑196/512，不删除未配对样本。manifest提供完整池、分角色GT及paired_by_role_GT统计。输出默认在私有目录，临床原文、reason及证据来源不公开。

编码复用105的精确offset及原分段loss：组0为prompt/pad，组1仅序列化时定位的verdict字符串值，组2为其余JSON、reason及EOS。reason即使出现Supported/Not Supported等词也不能变成标签loss。继续使用loss105的两段分别归一后相加，不新加权；实际后续训练预算和科学对照须另行确定。CPU自检只证明合同与实现，不证明reason监督有效。

## 原生reason回读

`parse127.inspect_output`复用原`parse105`的分类结果，并单独检查reason是否存在且为非空文本。可用`require_reason=True`记录漏输出理由；不因理由格式问题改写标签，也不把reason中的标签词当成判定结果。截断、重复JSON键沿用原parser处理。

结构有效不代表1—3句约束、医学语义、证据忠实性或reason与verdict的一致性已通过。训练数据的句数与语义由已保存审读记录确认；未来真实推理仍需单列这些检查。该CPU工具不调用模型，不改变120／128接口。
# 研究解释边界（2026-10-30补充）

当前接口先生成verdict，后生成reason，自回归分解为`P(verdict, reason | input) = P(verdict | input) × P(reason | input, verdict)`。因此，后写解释在本次推理中不会直接影响已输出的标签；训练时reason损失仍可通过共享参数改变分类。不能把更好的文字解释自动解释为更好的判别依据。

[Distilling Step-by-Step（Hsieh等，2023）](https://arxiv.org/html/2305.02301v2)在第3.2节使用任务前缀区分标签预测与理由生成；第4.4节的T5实验中，串接理由和标签有时低于普通微调，多任务表现更好。这提供了“不应把理由串接视为必然增益”的直接依据，但其模型、数据与损失不同，不能替代105／127在临床任务上的真实评价，也不能由此宣布105失败原因已查明。

[Jacovi与Goldberg（2020）](https://aclanthology.org/2020.acl-main.386/)强调区分解释的不同评价目标。[Measuring Faithfulness in Chain-of-Thought Reasoning（2023）](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning)通过干预发现，输出理由对答案的影响因任务而异。对本项目的含义是：引用匹配、语义成立、与标签一致、对预测有实际作用是不同问题。129只证明模型响应空reference，不能认证非空条件下的医学解释或内部推理。

这些文献不构成新训练启动指令。当时40对是准备资产，不是已验证有效的数据配方；若继续本方向，必须先有足够的真实关系覆盖并形成一个有区别、可检验的候选，避免仅改字段或堆数量后重做105。
