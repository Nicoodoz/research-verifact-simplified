# 093 交审说明

独立审计未执行。优先核查：1401原包与历史材料精确一致；F共享表展开等于B；A保留全部B来源、同患者原候选、字符/数量/每note限制；120冻结ID与152物理主请求的别名；153回执预算；raw/core不同分母、两条无效无旧答案填充；自然wrong→wrong导致false-S变化；压力raw救回和final救回ID不同；同患者集中及无重复的不确定性。

主指标调用现行evaluate/paired_compare；另用sklearn和Decimal核查矩阵/PA/MCC/MacroF1及费用，见selfcheck.json。补充递归字段隐私及链接检查见supplement_selfcheck.json。首次隐私扫描将自写decision.reason误认成模型reason字段，已仅对该报告字段作例外并重查通过；没有删除真实模型解释来掩盖泄漏。source_manifest记录历史材料未变。

只发布哈希/ID/指标与抽象病例关系。原临床文本、请求与回执仍在忽略目录，不提交。无独立holdout、无统计等效结论、无全量升级。本轮完成后停止，不恢复092训练、085或094。
