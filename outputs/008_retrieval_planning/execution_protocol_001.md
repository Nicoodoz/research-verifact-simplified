> 阅读镜像：已省略10行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# 008 执行前冻结协议

本协议在首次 008 API 调用前登记。基础版本 b03a230c0caa05b6198b2d9a2d988c3ef6c05a0b；执行代码和准备材料以 authority_001.json 与 preparation_001/manifest.json 的哈希为准。普通 README、AGENTS、审计文件不属于回执重放的不可变输入。

## 研究范围和动机

005/006 提示来源上下文可能改变解释范围，不能作为自证事实；007 发现来源查询既可能找回遗漏证据，也可能引入无关事件，且同输入重复生成和预算截取造成混淆。008 固定原医生标注的 atomic claim，研究“先说明需要寻找什么、再生成短查询”能否改善患者 EHR 获取。未宣称等价复现作者的向量库、切分器或完整检索流程。

固定开发患者第 13–18 名及 144 条 claim，详见 preparation_001。原有效标签用于选样和事后评价，不进入 planner、embedding 查询、reranker 或 Judge。患者组复用 003，不接触 reserved test 病例。

## 统一检索与三种查询

- 索引：同患者原始 EHR，沿用 007 的目标住院日历日范围 CHARTDATE ∈ [ADMITTIME 日期, DISCHTIME 日期]，排除 discharge summary。不是按 HADM_ID 声称精确过滤；不能解决原始日期异常，也不分析跨住院证据。每段保留原记录 ID、完整原文字符区间、日期及哈希。按空段分段，超过 640 字符在空白处分块，所有非空白字符保留。
- 基础检索：BM25（k1=1.2,b=.75，明确分词规则）与 Pro/BAAI/bge-m3 dense embedding，各 top80，以 RRF k=60 合并。服务只提供 dense，不声称使用 BGE 的全部 sparse/multi-vector 模式。
- direct：原 atomic claim 一个查询。
- simple：原 claim + 同 BHC parent 中与 claim token Jaccard 最高的字面 sentence + parent 及其前 240 字符的局部来源窗口。没有字面 sentence 时用 parent。去重相同查询/排名，不人工挑选有利句。
- planner：同一 DeepSeek-V4-Flash 看到原 claim 与上述局部窗口，输出原 claim 的证据需求、可核对的来源引句、术语对应、0–2 个短查询及不确定性。原 claim 查询始终保留。source-only 限定不是硬过滤条件，查询不得仅寻支持；不生成假设患者记录作为证据。具体提示已冻结。
- 多查询候选：原 claim 排名权重 .5，其他查询平分 .5；保留 direct 的前 8 个候选，再按 RRF 填满至最多 48 个。direct 也最多 48。候选扩展可能挤掉排名较低的 direct 证据，必须诊断这一代价。
- 三臂候选并集只调用一次 Pro/BAAI/bge-reranker-v2-m3，query 严格为原 claim，取得每个 passage 对同一 claim 的评分，各臂再限制到自己的 48 个候选。原文本含日期和类别，模型前缀、服务参数和返回别名如实记录。每文档只有一块，所有输入远低于服务长度限额。不将 planner 的需求列表或来源传给重排器。
- 按共享评分选证据，最多 16 个完整 passage、每 note 最多 2 个、正文加显示记录头上限 8000 字符，住院总头另加；相同日期/类别/原文去重。超过预算则跳过整个 passage，不截掉命中部分，不用任一臂的实际长度清空其他臂；记录全部跳过原因。相同上限不意味着相同实际 token 数，须报告差异。

## 生成、复用和失败

planner 与 Judge 均为 deepseek-ai/DeepSeek-V4-Flash，temperature=0、enable_thinking=false。planner max_tokens=1500、json_object；Judge max_tokens=2048，沿用 004 common+structured 提示和响应 schema。Judge 只接收原 claim 与实际选入的 EHR；检索来源文字不附加给 Judge。

planner 非 stop、截断、非法 schema、不可字面核验的来源引句等均留存失败诊断，并按预设退回原 claim 查询（ITT）；不修补输出、不挑选较好的生成、不补跑其答案。其余 schema 合法不等于医学含义正确，另作案例分析。

生成前以完整原生 Judge body SHA 去重，同 body 只保留一个固定 canonical 请求；三臂逻辑分配表引用同一个结果。预设另外 12 次 direct 完整输入重复，每患者每作者固定哈希取 1 条，仅作波动诊断，不能覆盖 canonical 或影响主指标。最多 432 个逻辑 Judge 条件 +12 次诊断，实际收费次数由冻结后的 body 去重决定。执行顺序固定哈希混排。

HTTP 200 原回执永不重生成。没有答案的余额错误自动切下一账号；未知发送结果、服务错误暂停，保留保守费用预占，人工检查已保存回执后才用单独登记恢复；不得因为结果不好重试。Judge 非法标签或截断不补标签，相应完整配对受阻，不悄悄做 available-case。

## 预算

依用户最新长期授权，预计任务新增总费用 ≤40 元直接执行，超过须明确批准。本次预计约 8.85 元（峰值单价、Judge 缓存前 444 次估计），阶段保护上限 planner=8、embedding_base=2、embedding_plans=2、rerank=8、judge=20 元，总和 40。公开价格：DeepSeek V4 Flash 输入未缓存 3、缓存 .3、输出 9 元/百万 token，02–08 点半价；两种 BGE Pro 输入 .07 元/百万 token。来源保存在 docs/sources/008_retrieval_planning。

每次发送前按 UTF-8 字节保守预占输入、最大输出及包装余量，回执 usage 可验证时按公开价格结算估计；缺失 usage 保留预占。费用包括 planner、embedding、reranker、Judge 和诊断；分别报告，不能把 embedding 或共享重排当免费。按阶段固定路径和 manifest 防止重新启动预算。账号余额 16 元不等于任务预算，不能因换 key 重置任务限额。没有收费 API 预检。
