# 039 Full-EHR Attribution Audit

目标：解释038/036中U2 Supported翻转究竟来自C48已有证据、C48漏检、部分支持还是未找到清楚支持。

执行：
- 462条claim-only query expansion；
- 遍历036目标住院eligible EHR完整dense/BM25排序；
- 原C48 + 32个最高排名C48外passage做GT盲Qwen证据审计；
- A/B/C/D/U归因只作post-hoc mechanism analysis。

结果入口：outputs/039_full_ehr_attribution/report.md
核验：outputs/039_full_ehr_attribution/verification_001.json
独立审计待进行；不自动修改036方法。
