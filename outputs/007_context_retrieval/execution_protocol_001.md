# 007：来源上下文辅助 EHR 检索

运行前方案。目标是比较查询构造的影响，最终 Judge 始终核验原 atomic claim。费用按用户长期授权处理：预计任务总费用约 ¥6.44、不超过 ¥16，直接执行并登记，不另行收费预检。尚未生成结果时写入本说明，执行结束后追加当前结果入口。

## 能重建什么

作者固定版本 `f115d36cb65fa2073fce0a10df56bb37f4cbcd50` 中，JudgeSubject 将 proposition 文本交给 ReferenceContextMaker；后者按患者/事实类型、CHARTDATE 的目标住院日历日期过滤，构造 dense/sparse/hybrid 检索、文本去重、rerank 和按时间排列的 reference。服务使用 BGE-M3 和 BGE-Reranker-V2-M3。release 有实际最终 reference，但没有索引快照、原始 EHR 事实节点/向量、完整候选分数或精确服务版本；源码快照也不能证明发布结果由该版本完整生成。007 不伪称等价复现，不运行缺失的原检索服务。

新建可复查 BM25 词面基线：只索引选中患者的原 EHR，按 ADMISSIONS 的入院/出院日期（包含首尾整天）限制 CHARTDATE，排除 discharge summary；保留实际 HADM_ID 供回查，不用其代替已声明日期规则。索引单元为原记录空行段落，超过 640 字符在空白处分段，不改文本，保留 note ID、日期、字符偏移。验证所有已索引非空白字符无遗漏。检索代替方案与原 VeriFact 在事实单元、模型、索引、预算及去重上不同；不以新成绩相对发布成绩的差值推断查询贡献。

## 固定设计

- 新验证患者为 003 开发哈希顺序第 9–12 名：21706、55204、65399、47874。前八名已用于 004–006，不作为独立新验证，reserved test 不用于方法选择。
- 从 406 条 valid claims 按固定 ID 哈希分层选 96 条，每患者/作者 12 条，先最多各 3 条 NS/NA，再以 S 补齐。LLM 为 39 S/5 NS/4 NA，human 为 27 S/9 NS/12 NA；不是自然类别分布或完整患者队列成绩。所有候选/未选 ID 保存，不按旧预测选样。
- 四臂：`claim` 原 atomic claim；`sentence` 同 BHC、在 parent 内逐字出现且与 claim token Jaccard 最高的既有 sentence proposition；`local` 完整 parent 加前方最多 240 原字符；`mixed` claim 与 local 各取前 100 后等权 RRF，分数为 `1/(60+rank)` 之和。仅 retrieval 查询使用来源文本。sentence 不是默认优于 claim，local 中不一定只有相关断言。
- BM25 固定 k1=1.2、b=0.75、平滑正 IDF；查询词二值化，简单小写词/数字分词并保留否定，数字前导零归一化；不使用医学同义词表或 LLM 改写。mixed 多一次免费的本地排序，不增加最终证据/模型调用预算。
- 证据先从各排序前 100 中取最多 24 片段、上限 9,000 字符；再按同一 claim 四臂实际可用量的最小值统一预算。末片可在空白处分割，仍是可定位的原记录子串。仅同日期/类别/逐字文本去重，保留不同日期重复事件。按时间排序、标注 note ID/偏移后交 Judge。四臂平均完整 reference 约 7,764–7,772 字符，不声称严格等 tokenizer 数，另报真实 usage。
- 四臂 Judge 相同：SiliconFlow DeepSeek-V4-Flash、temperature=0、enable_thinking=false、max_tokens=2048、原 004 common＋structured 提示及相同 JSON schema。输入数据字段仅 `proposition` 和 `reference`，不含来源上下文、查询、作者或 GT。模型别名不是不可变权重版本。
- 四臂共 384 次请求；每患者/作者再以固定哈希选 1 个 claim，追加相同原生 body 的 `claim_repeat`，共 8 次，合计 392。重复只用于服务变异诊断，不替代原预测、不选优，四臂每个 claim 只保留原始响应。臂顺序按 24 种排列平衡；预设初始并发 2。
- 默认主比较 mixed−claim；sentence−claim、local−claim 为诊断比较，也报告其他两两关系以理解粒度差异。全部使用 002 evaluate/paired_compare，三分类 micro PA/AC1/MCC、valid-only、固定队列、1,000 次患者 bootstrap，作者分开。缺失、非法标签或截断保持失败，完整作者/臂/配对才评分，不做 available-case。
- 通信未知先暂停并核对本地空响应回执，登记为未重发失败，保留费用预留，仅继续未发工作；已收回答不因标签/格式重跑。余额无答案错误按原池切换账号。所有尝试跨账号合计、受 ¥16 与每请求最多 5 次限制；不重置预算。

## 离线定位与解释边界

005 C13/C16、006 N15/N23/N45 的关键证据已在 reference，不能直接归为检索失败。N25 的两个片段是否同份 ECG 是证据来源组织问题；本轮可连接到原 note 267779。N50 实际 reference 没有左 EVD 撤除片段，同患者其他 reference 有；新 claim-only 已能找回 note 458866，所以不能把找回当作上下文独有收益。

C17/C18 和 N56 存在来源可提供事件/剂量限定的情况，但单独 parent 可能仍不含前文的关键日期。于是通过已分析病例的离线检查，把最终较宽查询统一设为 parent＋前 240 字符。这是生成新病例 Judge 结果前的设计修订，不是按新结果选最优。C17 的对应再操作耐受、C18 的精确最终剂量反应尚未被充分建立，不能给这些病例伪造检索 gold evidence。

保存的关键词锚点只作已读案例的可定位诊断，不是全量临床 Recall@k 金标准。新结果要同时查看改善、退化和稳定对照的原输入/完整输出及证据；比较正确事件/状态是否加入、是否丢失核心证据、是否被无关来源事实带偏。相同 reference 的跨臂差异和 8 个重复请求用于提示 Judge 波动；不同证据下的单次答案不能证明内部因果机制。

当前正式冻结输入为 [preparation_003](../../outputs/007_context_retrieval/preparation_003/manifest.json)。preparation_001 的段落正则遗漏已在发送前发现，保留为拒用快照；preparation_002 修复索引后用于发现 parent 不足，之后由 003 替代。两者均未发送。原始数据、001–006 历史 run 和审计意见不修改。

主要实现：`retrieval.py`、`prepare.py`、`offline_checks.py`、`run_judge.py`。原算法主来源：[固定作者 ReferenceContextMaker](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/reference_context.py)；[BM25 说明](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html)；[供应商有日期的价格公告](https://docs.siliconflow.cn/docs/release-notes/overview)。
