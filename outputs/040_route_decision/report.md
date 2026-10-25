# 040：039后研究路线决策

## 结论

040按事先写入protocol的规则读取039结果，不做新API、不调任何分类参数。

有效R共216条：A=66（30.56%）、B=55（25.46%）、C=94、D=1。A+B=56.02%，但A本身不到50%，且B没有超过A。因此039结果既不满足“decision-boundary dominant”，也不满足预设的“retrieval-dominant”条件；同时A+B又超过50%，也不满足“evidence/scope mismatch dominant”。

**因此040不强行挑单一主因，而记录为 mixed mechanism：decision boundary、retrieval coverage和evidence/scope mismatch并存。**原protocol没有显式覆盖这个混合区域，这一点保留记录，不事后修改门槛制造winner。

## 对041的决定

041继续，但功能被限制为**选择性证据门控解释同步**，不是默认解释重写器：

- 同时报告C48-only与A+B expanded两个工作点；
- 不根据reserved结果再选其中一个winner；
- A/B才允许生成Supported解释，C/D/U必须abstain；
- 解释只由已验证的逐字证据quote确定性渲染，不再调用LLM根据final label自由改写；
- H/W中A+B为32/123（26.02%），所以必须把false-justification作为核心风险指标。

## 对论文主线的决定

主线从“λ修复核验能力”正式收紧为：

1. decision boundary改变label agreement；
2. retrieval coverage决定部分claim是否获得足够输入证据；
3. evidence sufficiency与医生claim-level GT存在不可忽略的scope差异；
4. explanation synchronization只能建立在独立证据约束之上，不能把final label直接作为生成理由的条件。

040本身0 API、0费用，不启动新的分类器搜索。
