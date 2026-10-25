# 027 成果入口

唯一必读：[中文主报告](report.md)。当前为执行、自检完成，**待独立审计**；没有新winner或新Gate。

| 路径 | 内容 |
|---|---|
| protocol_001.md | 新诊断计算前登记的方法与边界 |
| analysis_002/ | 正式：155候选、全阈值曲线、完整global、作者/患者排序、组成、概率分布、冲突组、bootstrap |
| interpretation_001/ | 固定点平台、概率尺度、Q警报交叉表、计算线性项；不重训 |
| case_material_001/ | 固定31例完整claim/reference及两模型输出 |
| reading_view_001/ | 完整片段去重阅读视图与每例块映射；只压缩空白，原文在case_material |
| semantic_001/ | 31例执行者文本观察、53处原文偏移；不是医学gold |
| figures_002/ | 正式PNG/SVG：完整风险曲线、高rescue区、分数分布 |
| verification_001/ | 自检、单元测试与重放记录；不代替独立审计 |
| audit_handoff.md / handoff_001.json | 审计重点、重放入口和被审指纹 |

analysis_001为参数重算概率初算；analysis_002精确读取026保存概率。figures_001为首稿，figures_002修正高rescue阶梯方向。不覆盖早期材料，不把它们当额外实验或方法版本。
