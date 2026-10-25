# 009 论文写作底稿（可选阅读）

这份底稿用于后续论文，不替代[简明主报告](report.md)。数值来自冻结确认队列；案例为执行者解释，无新增医学gold。以下不是已获独立审计的结论或投稿成功承诺。

## 可直接使用的实验设置

**任务。** 输入固定atomic claim和已知患者的既有EHR，输出Supported / Not Supported / Not Addressed。所有方法核验同一原claim，不向Judge添加来源BHC；沿用VeriFact-BHC v1.1.0原有效性与医生标签。评价衡量原标签一致性，不能自动等同于语境恢复后的医学正确性。

**队列。** 003预先冻结20探索、40开发、40保留测试患者。008已用开发顺序13–18位的144条类别加密命题用于009方案开发，不称独立样本。009确认使用随后6名患者全部650条有效命题：LLM243、人写407，无结果导向抽样。确认方案、身份清单、模型设置和评价规则在新患者首个请求前保存。保留16开发及40测试患者。001/002已有总体分析，不声称测试数据此前完全未接触。

**语料。** 使用本地患者EHR，按患者身份与目标住院起止日CHARTDATE过滤，排除discharge summary；其他住院和元数据时间异常遵从已记录的筛选边界，不凭目标admissions假装覆盖全部历史住院。最终413份note切成2,498段，空段不建索引，所有非空白原文有覆盖；先按空行分段，长段在640字符内的空白处分开。每段保存原始note ID、字符区间、日期、时间、类别与哈希。索引用搜索文本为日期、类别、description及原段文本。

**基础检索。** 原claim检索同患者索引。BM25参数k1=1.2、b=.75，定制停用词及tokenization以冻结源码为准；它不是learned sparse。BGE-M3取1024维dense向量，cosine排名，无额外query instruction。两路各最多80项。

**条件。** A48为等权RRF，score(d)=Σ(60+rank_r(d))^-1，再取48；B48为dense前48；C48依次交替dense/BM25未见ID，累计48。重合候选只占一次，因此每路前24均可保留且会自动进入更深排名。573条每臂48候选，77条语料仅47段。这里的C是可解释的容量控制，不包装成算法创新。

**重排和打包。** 三臂候选并集共38,893个query-document配对，由Pro/BAAI/bge-reranker-v2-m3真实计算；query始终原claim，max_chunks_per_doc=1，保存全部索引/分数，各臂只在各自候选中排序。每次最多16段，每note最多2段，重复按同日期／类别／逐字文本去除；正文及逐段头部最多8,000字符，住院头额外计入。整段不截断，按日期／时间／note ID／原位置展示。分数是相关性，不是临床支持概率。

**Judge。** 硅基流动deepseek-ai/DeepSeek-V4-Flash，普通structured提示及schema沿用004，temperature=0、enable_thinking=false、max_tokens=2048、n=1、stream=false。三臂完整请求事先去重，1,950逻辑条件对应1,303 canonical body，另12次原body重复，共1,315次实际请求；重复不覆盖原答案。供应商只给模型别名，未验证不可变权重版本。

**评价。** `verifact_research.evaluation.evaluate`及`paired_compare`；valid-only、固定3类、micro PA/AC1/MCC，作者分别分析，1,000次患者cluster bootstrap，随机种子0–999。B−A为主比较，C−A及C−B为冻结次要比较；无缺失、无available-case补标签。输出全精度差值后取整。主要结论取自同期新队列，不比较不同任务/患者上的绝对MCC。

## 核心结果表

|作者|方案|N|PA|AC1|MCC|相对A改对／改错／错类变化|
|---|---|---:|---:|---:|---:|---|
|LLM|A48|243|.8025|.7757|.2652|—|
|LLM|B48|243|.8066|.7803|.2857|13 / 12 / 1|
|LLM|C48|243|.8025|.7758|.2654|6 / 6 / 1|
|human|A48|407|.7641|.6960|.5114|—|
|human|B48|407|.7150|.6262|.4587|16 / 36 / 8|
|human|C48|407|.7715|.7058|.5272|10 / 7 / 4|

完整bootstrap区间、各类precision/recall/F1及support、逐患者表见[synthesis_001](synthesis_001/)。同输入重复确认1/12次翻转；不能据temperature=0假定确定性。另9个事后困难案例中的18次重复有5次翻转，选例条件不同，不能合并估计普遍随机率。

**开发对照。** 旧144条C−A净增每作者各1条；B−A净损LLM3、human5。固定24条（每患者每作者2条哈希取样）的容量/重排/每note诊断如下；LLM12条全部原GT Supported，因此其三类MCC退化为0，不解释为所有条件相同。

|条件|LLM正确数 /12|human正确数 /12|解释边界|
|---|---:|---:|---|
|A48|9|8|基准|
|B48|9|7|—|
|C48|9|8|—|
|A80|9|8|增容量未改变该子集正确数|
|B80|9|8|仅多对1条，不支持普遍扩容|
|B48无rerank|9|8|无重排用真实dense分数；小子集不证明reranker无用|
|B48每note最多16|7|8|LLM退化，不能全局取消多样性约束|

**费用。** 全部阶段合计¥18.08218167，2,692任务／2,700 HTTP尝试。8次402无答案错误计0后切账号；无未知费用预留、无不可恢复缺失。包含开发重排漂移后的刷新、旧批次、确认、重复及52个新增诊断Judge请求；008缓存答案不再次计费。计费依据为供应商usage（rerank在meta字段）及运行日期公开价格，非发票。

## 能够写入讨论的结论

**得到本轮确认的结果：** 在固定650条新开发命题上，dense-only没有整体优势，人写Supported召回明显下降；C保留两路候选且取得近似或稍高点估计，但没有证明稳定优势。明确证据损失同时出现在早期候选门槛、重排后的选择约束、以及基础召回；不存在一个已证实解释全部错误的唯一瓶颈。

**有原文与控制支持的探索观察：** N302补回/移除实际bolus段及背景对照方向一致；N293证据补回仍不能消除前后状态冲突的解释；N561/N563检查身份与结果被分开；N487等案例显示匹配证据与原标签得分可能不一致。这些是病例层面的诊断干预，不是人工挑证方法的部署成绩，不计算oracle主指标。

**实现修正，不能算论文贡献：** planner纯空白校验恢复28例、预算与断点恢复、完整body复用、历史重放分离、浮点漂移检测。128份计划可解析不等于128份医学正确计划，16份仍退回；没有重新计算修正版planner成绩。

**仍未得到的证据：** C的跨队列稳定增益；新的证据组织策略效果；planner在更合理direct链路上的额外收益；独立临床证据相关性/充分性gold；最终reserved-test性能。本轮不能把某个未知项写成已证实贡献。

## 相关工作定位草稿

VeriFact已把临床文本命题与患者EHR检索结合，本研究保持原标注单位与标签，研究的是检索到的证据在后续候选保留和打包过程中如何失效。作者固定代码默认BGE dense与learned sparse、Qdrant distribution-based score fusion及原query重排，与本地BM25＋RRF替代实现不同，不能用009数值声称原系统复现优劣。[作者实现](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/reference_context.py)

BGE-M3提供dense、learned sparse和multi-vector模式，官方建议混合检索加重排；这不保证任意候选容量与证据选择规则都更好。本轮区分逐路召回、分臂资格、共享API重排及最终reference，而不将组件推荐视为任务效果证明。[模型卡](https://huggingface.co/BAAI/bge-m3)、[重排模型卡](https://huggingface.co/BAAI/bge-reranker-v2-m3)

Query2doc通过LLM生成伪文档扩展查询；Query Rewriting采用Rewrite-Retrieve-Read，已有“为回答找所需知识”的思路。本研究不把生成式查询作为创新起点，而检验它的表面收益是否由基础链路丢失已有候选所造成。[Query2doc](https://aclanthology.org/2023.emnlp-main.585/)、[Query Rewriting](https://aclanthology.org/2023.emnlp-main.322/)

RARR生成核验问题、检索后归属和修订文本；医学Step-by-Step Fact Verification也已用后续问题，但其一般医学声明、证据源和排除NEI的评价与个人EHR三分类不同。本研究保持原claim不变，来源仅作潜在查询线索，关注证据与原标签的一致性不能等同这一边界；不能声称首次医学检索规划。[RARR](https://aclanthology.org/2023.acl-long.910/)、[医学逐步核验](https://aclanthology.org/2025.naacl-short.68/)

上述论文范围沿用[008定向原文阅读](../../tasks/008_retrieval_planning/research_notes.md)，009补充官方模型/代码核对；没有声称完成系统综述或逐页重读全部附录。下一步若验证统一证据组织，贡献应由同claim、同候选、同预算的受控效果支撑，而非把“换融合公式”命名为新方法。
