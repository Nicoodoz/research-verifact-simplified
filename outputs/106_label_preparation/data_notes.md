# 106数据准备：候选可用，关系收益尚未认证

最终决定先在104原196条上隔离检查标签目标归一因子。下列两个512条数据包是已经准备好的后续数据候选，**不是下一轮实际GPU训练配置**。固定三对源文核查提供了反证，因此不将教师分歧及词法最近邻包装成已确认的临床边界覆盖。

## 范围与原始数据

只从103原40名训练患者的3675条原命题取样；原claim、各自原reference和医生最终GT均未改写。以受限本地SQL连接核对proposition ID、患者、作者、GT、claim和reference；不读后续40确认患者的临床正文、标签或预测来选方法。

|集合|S|NS|NA|总数|患者|
|---|---:|---:|---:|---:|---:|
|完整训练池|2893|297|485|3675|40|
|103原样本|320|96|96|512|40|
|104保留|83|62|51|196|40|
|104隔离|13|34|45|92|38|
|104未语义审查|224|0|0|224|40|
|ordinary_sample|320|96|96|512|40|
|boundary_cover|320|96|96|512|40|

104首判为S、GT为NS10/NA6的16条当时全部隔离，没有因本轮教师同意或多数投票而改GT。本轮其中12条进入两个候选的共同部分，4条两边均未选；逐条去向见[data_104_supported_disagreements.jsonl](data_104_supported_disagreements.jsonl)。这不等于16条都已证明是可辨别难例。

## 严格匹配的候选

`boundary_cover`每个non-S类别固定64条既有paper_r1预测S、32条既有paper_r1的NS/NA互换；同患者分散，桶内按固定教师分歧及词法排名。教师错误仅是困难代理，并非当前9B训练预测或新语义gold。S320优先纳入实际选中non-S的患者内最近原S，其他槽位按固定排名补齐。

`ordinary_sample`在相同患者×GT×作者×实际prompt长度四分位×104既有语义状态的每个槽位内独立固定hash抽样。两臂每个训练位置的上述五项相同，各human380/LLM132；重合217条。不以教师是否同意GT为准入条件，保留同等既有争议负担。

两臂保留完整原reference。最终prompt输入tokens总量分别为4,312,348和4,308,456，差0.0903%。这是关闭thinking后实际104/105共享prompt的前缀token数，不是reference原文词数；答案及EOS另计。现有CPU桥接使用冻结9B tokenizer文件与既有032环境tokenizers0.22.0，无权重加载，GPU环境版本差异由后续桥接检查约束。

已知104输入缺口14条对两臂统一排除。固定中位pair核查另发现1条具体输入缺口，额外合法EHR明确存在目标药物继续使用处置，但本条actual reference遗漏该动作；保留原GT、对称隔离，未偷偷补证。详见[data_isolation.jsonl](data_isolation.jsonl)、[额外EHR核查](data_ehr_gapcheck.json)。初始受审候选及原pair清单保存在私有`drafts_v1`，103—105工件不改。

## 会改变设计的反证

初稿192个non-S均有一个患者内最近S双端入选，但这只是词法索引性质；初稿10对相似度低于0.1，所有对均使用不同reference。事前按相似度最低、中位、最高固定3对，逐对完整审读两条各自实际reference，未重选以避开问题：

- 最低对无临床目标关系，S只能算普通正例填充。
- 中位对只是专科主题相近；non-S当前输入缺药物决定，额外合法EHR找到了遗漏处置，已单条隔离。
- 最高对几乎同义但GT相反，存在多次操作及未解析指代；不认定任一医生GT错误，也不将它认证为可学习的关系对。

因此不声称有192个临床保护对，不将3对结果外推为全部192对的失败率。源文指针及抽象判断见[semantic_training_pairs.jsonl](semantic_training_pairs.jsonl)，原始引文仅保存在私有目录。新增隔离后按同一规则重建候选，原三对审计仍绑定隔离前的固定清单。

## Claim-only探针与检查

固定词TF-IDF(1,2)+LogisticRegression(C=1)，五折按患者分组，词表仅拟合训练折，含多数S对照，无参数搜索。完整3675条OOF：PA80.27%、MCC0.2455；多数S为78.72%/0。探针NS召回为0、NA召回16.70%，高PA不能当证据理解。

使用同一套3675条OOF预测比较104保留196、隔离92、unresolved78、未审224S及两个新512候选，不重拟合以选择数据。逐GT正确数、false-S及统一指标见[probe_results.json](probe_results.json)。另保留196单独CV结果，但其训练量和类别先验不同，不能把两种训练分数之差解释为筛选的因果效应，更不能预测9B效果。

实际数据检查覆盖：原文/GT/reference未变、训练与评价患者/ID隔离、同位置五维匹配、固定困难配额、原S各自合法来源，以及对reference/GT/prompt/患者篡改的拒绝。它们验证数据和实现，不证明临床有效性。新增收费API为0，GPU为0。

私有可训练入口为`.local_models/106_label_preparation/ordinary_sample.jsonl`和`boundary_cover.jsonl`；公开入口为[data_manifest.json](data_manifest.json)、[data_matching.json](data_matching.json)、[data_pool_index.jsonl](data_pool_index.jsonl)。原文、完整引用、EHR及训练JSONL不随Git发布。
