# 131 source_context_probe

CPU诊断完成，无新模型推理或训练。固定选取120在687条内部复核中相对107新增的false-S：原GT为NS／NA各3条，6名患者，优先未经过127语义审读的ID，再按固定哈希选取。它们来自原8名内部验证患者，绝不转为训练样本。

读取6条完整既有reference，定位同住院日历范围、非discharge-summary原始notes。600个片段全部能按原元数据和空白归一后的子串定位，126个片段有多个匹配位置，保留全部候选，不声称唯一来源。随后只核查相关原文上下文，不通读132份原始note。

`source_context131.py`接收冻结的私有cases，输出限制在`.local_models`。它是源文定位工具，不判断医生标签、不构造新的模型输入、不把检索命中当作证据正确。已运行两项CPU检查：CHARTDATE与CHARTTIME日期不一致、同片段多份note匹配。

[结果](../../outputs/131_source_context_probe/report.md)。私有选样、600片段来源与语义观察位于`.local_models/131_source_context_probe/`。未新增GPU任务，未改变120／127数据和任何历史结果。
