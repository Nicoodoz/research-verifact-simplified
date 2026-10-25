# 012成果入口

**2026-09-15独立审计PASS，可冻结／结项。** 只需阅读[中文主报告](report.md)。650条三组对照、195条错误并集、24例固定深读完成；无新增API、费用¥0、无新患者。

保留C48作冻结实用对照；新增观察提示核验目标/支持范围与本地信息损失同时存在。建议优先验证前者，基本极性/条件保真作为窄工程前提；不是已证明新方法有效，也不重启011未执行main。

| 入口 | 用途 |
|---|---|
| [protocol_001.md](protocol_001.md) | 深读前固定的范围、框架与选择规则 |
| [alignment_002](alignment_002/summary.json) | 三组650条实际输入/输出绑定、初始选例；pending字样是阅读前快照 |
| [materials_001](materials_001/summary.json) | 24例完整材料、6患者已有EHR/索引；原始内容不修改 |
| [最终台账](diagnosis_001/ledger.csv) | 全650条、错误并集、正确对照、已查/未查和未知范围 |
| [24例诊断](diagnosis_001/diagnoses.json) | 观察、机制假设、反证、字面位置及全部生成输出的案例页 |
| [C链条](pipeline_001/summary.json)、[原EHR回查](raw_search_001/summary.json) | 全量机械检查与有限语义回查分开；不作为医学检索gold |
| [定向独立核查1](independent_checks_001/semantic_findings.md)、[2](independent_checks_002/README.md)、[3](independent_checks_003/README.md) | 重要结论与机器计数另行复核；不是全任务审计结论 |
| [audit_handoff.md](audit_handoff.md) | 执行者自查、真实版本、文件指纹及独立审计入口 |

`alignment_001`保留写CSV中止的历史草稿，`alignment_002`是正式对齐；没有按深读结果重抽案例。后续重放另建目录，不能覆盖以上正式成果。

当前独立状态见[012审计记录](../../reviews/012_comparative_error_diagnosis.md)。主报告与交审记录中的等待状态保留为历史；下一方法仍未验证，011停止决定不变。
