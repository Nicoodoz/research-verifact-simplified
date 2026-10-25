# 045：Semantic Recovery Route Screen

## 核心结论

045按低成本路线筛选方案完成第一批16条development诊断集，按协议停止，不自动进入第二批。

四条路线只有D（同一C48直接换Qwen Judge）出现正向分类信号：

| 路线 | 正确/16 | rescue | harm | 净变化 | raw标签变化 |
|---|---:|---:|---:|---:|---:|
| Base DeepSeek | 8 | — | — | — | — |
| A 改核验指令 | 8 | 0 | 0 | 0 | 0 |
| B Qwen语义选证 + DeepSeek | 8 | 0 | 0 | 0 | 0 |
| C DeepSeek反馈 → Qwen查询 → BM25补检 → DeepSeek | 8 | 0 | 0 | 0 | 0 |
| D Qwen直接Judge | **10** | **2** | **0** | **+2** | 2 |

4条固定同输入DeepSeek repeat全部与044 base一致，未观察到标签波动。

本轮新增76次API调用，全部HTTP200，usage估算费用 **¥0.993993 / ¥8**。这证明“小样本多路线筛选”足以迅速淘汰弱路线，没有必要先花几十元做大队列评价。
## 1. 诊断队列

从044已经使用过的8名development evaluation患者中固定选择16条，实际覆盖7名患者，reserved overlap=0。

设计上故意一半错误、一半正确保护对照：
- base错误8条：Supported 4、Not Supported 2、Not Addressed 2；
- base正确8条：Supported 4、Not Supported 2、Not Addressed 2；
- 尽量平衡human/LLM；
- 每患者最多3条；
- 满足配额后固定hash选取。

因此本轮用于**方法机制筛选**，不能把10/16等数字写成总体准确率。

Baseline直接复用044刚完成的round0 DeepSeek回答，避免重复付费；另固定4条原C48同输入repeat用于波动诊断。

## 2. A：只改Judge核验范围

C48、模型、temperature和结构化输出保持不变，只给DeepSeek增加：
- 不增加claim未陈述的要求；
- 后续变化不自动否定早期时间点；
- plan ≠ completed；
- possible/recommended ≠ certain；
- missing与contradiction分开。

结果：
- 16/16 raw verdict与原base完全相同；
- 0 rescue / 0 harm；
- 固定U2也无变化。

因此在这批病例上，**仅靠提示词明确边界没有转化成标签修复**。不能由此证明所有prompt优化无效，但A不值得进入第二批。
## 3. B：Qwen语义选证

Qwen读取：
- 原claim；
- 原C48；
- 044已冻结的rank / complement / time三个增量证据包。

它不知道GT，也不输出最终标签，只选择none或一个证据包。若选none直接复用base；若选包，再把真实EHR原文追加给DeepSeek终判。

选择结果：
- none：15/16；
- complement：1/16；
- rank/time：0。

唯一一次追加后DeepSeek标签也未改变。

因此B为：
- 0 rescue / 0 harm；
- 16条最终raw verdict与base完全一致。

这个版本的语义selector过于保守。它没有像043 oracle那样定位出足够有用的补充证据，不进入第二批。

## 4. C：反馈式定向补检

C允许新增在线推理环节：
1. 复用原DeepSeek初判与reason；
2. Qwen识别“还缺什么事实/关系”，生成最多2条查询；
3. 在同患者目标住院范围的031 EHR corpus上本地BM25检索；
4. 排除C48精确重复正文，最多追加2段、约1500字符；
5. DeepSeek重新终判。

16条中有7条实际得到新passage并触发终判。

但结果：
- raw verdict：7条全部与base相同；
- 总体0 rescue / 0 harm；
- 固定DeepSeek-U2反而出现1个harm，U2正确数10→9，false-S 3→4。

因此C第一版不进入第二批。
一个重要失败例是：

> A repeat speech and swallow study was performed on [2-3].

GT=Not Supported。原C48已经同时含有：
- 计划进行speech/swallow evaluation；
- 同日护理记录明确写“Refused speech and swallow this am”。

原DeepSeek仍判Not Addressed。C的gap模型正确识别“需要确认2-3当天是否实际完成”，也生成了针对查询并补检，但终判DeepSeek仍维持Not Addressed。

也就是说，该例不是主要缺在“没有检索到拒绝记录”，而是**DeepSeek没有把明确拒绝理解成对‘performed’的反证**。

这直接支持下一节的Judge差异解释。

## 5. D：同证据直接换Qwen Judge

D完全不改变C48，只让Qwen3.8-27b按相同三分类定义重新判断。

结果：
- base 8/16正确；
- D 10/16正确；
- 2 rescue / 0 harm；
- false-S仍为3，没有增加；
- 两个rescue分别来自一条LLM claim和一条human claim；
- 分别修复了GT=Supported和GT=Not Supported，不是单纯向Supported偏移。

4条DeepSeek同输入repeat均未变化，因此这两次D改判不能简单归于当前base服务的普通随机翻转。
### Rescue 1：可能GI bleed

Claim：

> The drop in hematocrit indicated a possible gastrointestinal bleed.

GT=Supported。DeepSeek base=Not Supported，Qwen D=Supported。

原C48本来就明确包含：
- hematocrit从29降到21；
- “first consideration would be GIB”；
- “concerned w/ GIB”；
- “Chief Complaint: hct drop, ? GIB”。

所以这里不是缺证据。Qwen正确保留了claim中的**possible**限定，而原DeepSeek对证据要求更严格。

### Rescue 2：吞咽检查被拒绝

Claim：

> A repeat speech and swallow study was performed on [2-3].

GT=Not Supported。DeepSeek base=Not Addressed，Qwen D=Not Supported。

原C48已有：
- speech/swallow evaluation计划；
- 同日“Refused speech and swallow this am”。

Qwen把“拒绝”理解为该声称已performed事件的反证，因此判NS；DeepSeek把它当成“没有performed记录”，判NA。

这两例说明本批次最值得继续研究的不是检索容量，而是**Judge对模态、完成状态以及NS/NA边界的处理差异**。
## 6. D的限制

D目前只能作为候选路线，不能宣布“Qwen更好”。

原因：
- 只有16条定向诊断样本；
- 本轮不是自然分布；
- 只有2个改判案例；
- Qwen输出中的checks.evidence_ids使用了Note ID字符串，而不是当前系统要求的编号reference ID，因此引用格式不合规。

两个rescue的reason内容已离线核对，关键事实确实存在于原C48；但在下一轮继续D之前，应先把Qwen输出schema改成严格的编号引用，不把本次格式缺陷带入后续。

另外，045分析里将固定λ=2也应用到了Qwen的label_scores作诊断；**这个结果不能作为D正式性能依据**，因为λ=2是在DeepSeek分数尺度上开发的，并未针对Qwen校准。D当前应看原生verdict+reason。

## 7. 成本

- Stage 1：68次调用；
- Stage 2：8次终判；
- 合计：76/76 HTTP200；
- Qwen调用48次；
- DeepSeek新调用28次；
- usage估算费用：**¥0.993993**；
- 保护上限：¥8。

本轮没有因为预算充足而自动扩大到第二批。

045显示：对于“路线选择”阶段，16条共同诊断病例已经能明显区分A/B/C/D，成本不到1元。相比044约30元的完整实验，筛选效率明显更高。
## 8. 研究决策

第一批后的路线状态：

- **A：淘汰当前版本。**
- **B：淘汰当前版本。**
- **C：淘汰当前版本。**
- **D：保留，值得进入下一批小样本确认。**

更深层的研究重点也发生变化：

> 当前一部分高价值错误不是“证据没有找到”，而是同一C48下不同Judge对模态、事件完成状态和NS/NA边界作出了不同判断。

043仍说明定向补证据能救回另一类错误。因此后续不应只押一个机制，而应区分：
1. evidence-missing型：需要定向补检；
2. evidence-present-but-misinterpreted型：需要更好的Judge或专门的关系/状态核验。

045第一批给D提供了进入下一轮的理由，但没有给“换Judge全面替代当前系统”提供证据。

## 9. 完整性

- GT未发送给任何045新API请求；
- 所有病例来自development，reserved overlap=0；
- 76次请求全部HTTP200，无结果选优重跑；
- 4条baseline repeat全部稳定；
- 执行者核验状态：PASS_WITH_D_CITATION_FORMAT_WARNING；
- 独立审计未执行。

主要入口：
- cohort.jsonl
- stage1_jobs.jsonl
- stage2_selections.jsonl
- analysis_summary.json
- changed_cases.csv
- verification_001.json
