# Task 043 — Targeted Evidence Utility

目标：验证039定位出的新增EHR证据，真正交给原DeepSeek scoring Judge后，是否能让Judge自己改变判决并生成与新判决一致的reason。

这是reserved后的post-hoc机制实验，不是新的无偏性能测试，也不用于方法选择。

三条件：
- A：原C48；
- B：原C48 + 039实际引用的目标证据；
- C：原C48 + 同数量matched context控制。

主要结果：B相对A在普通DeepSeek verdict上13 rescue / 0 harm；B相对C 14 rescue / 3 harm。

主报告：../../outputs/043_targeted_evidence_utility/report.md
执行者核验：../../outputs/043_targeted_evidence_utility/verification_001.json

独立审计：待进行。
