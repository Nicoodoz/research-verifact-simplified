# 065：Verification-oriented Evidence Construction Screen

## 研究问题

064以前主要在Judge输出之后做校准/后处理。065前移到Judge输入，验证：

> 如果不改Judge、不加U2/PriorG/Gate，仅改善“核验需求 → 证据检索 → 最小充分证据呈现”，DeepSeek raw verdict能否直接更正确？

本轮只做development机制screen，不使用reserved，不自动扩confirmation。
## GT-blind screen cohort

来源：044 evaluation development池，必须有031 C48与eligible EHR材料。

选择完全不读取GT：
- 8名044 evaluation患者；
- 每患者固定取1条 raw DeepSeek verdict 与固定U2不同的boundary claim；
- 每患者再取2条 raw=U2 且max(label_scores)>=80的stable protection claim；
- 患者内均按固定SHA256排序选取。

共24条，每患者3条。

GT仅在三臂全部prediction封存后用于分析。
## 三个arm

### A：Baseline
- 当前044 E0/reference；
- 同一DeepSeek-V4-Flash-0731 scoring Judge；
- 只使用raw verdict作为主终点。

### B：Focus-only
- 不访问C48之外的任何EHR；
- 对031同一C48候选池进行verification-oriented evidence composition；
- 最终DeepSeek只看到composer选出的原始C48 passage；
- 不保留Qwen摘要、判断或标签。

### C：Retrieve+Focus
- 先做claim-only verification plan；
- 在同住院eligible EHR中做requirement-aware高召回检索；
- composer从“原C48 + 新检索候选”中选择最小充分原文证据集；
- 最终DeepSeek仍只看到原始EHR passage。
## Verification planner

Qwen3.8-27B non-thinking，temperature=0。

输入仅claim。输出JSON：
- requirements：1–6条该claim真正需要核验的事实/时间/关系/确定性；
- queries：1–4条保守检索query。

必须保留：
- 时间限定；
- 否定；
- possible/suspected/confirmed等确定性；
- planned/ordered/refused/completed等事件状态；
- 数值/趋势/前后关系。

Planner不得输出最终S/NS/NA。
## C臂 requirement-aware retrieval

复用031 frozen eligible corpus与embedding。

每claim构建排名：
1. 原claim dense；
2. 原claim BM25；
3. 每条planner query BM25；
4. 每条requirement BM25。

使用RRF融合，排除C48已包含passage及正文精确重复。

取top24 external candidates，供composer使用。

不调用新的embedding API。
## Evidence Composer

B/C使用完全相同Qwen prompt与规则。

输入：
- claim；
- planner requirements；
- candidate raw EHR passages。

B candidates = 原C48。
C candidates = 原C48 + top24 external。

输出JSON：
- selected：3–8个candidate ID；允许少于3，仅当候选确实不足；
- coverage：每个requirement对应哪些selected IDs，或unresolved；
- why：简短选择理由。

选择原则：
- 每个material requirement尽量被直接覆盖；
- 同时保留material contradiction/counterevidence；
- 优先明确原文，避免重复、背景噪声和仅语义相关但不能核验限定条件的passage；
- plan≠completion，possibility≠certainty；
- 不输出最终S/NS/NA。
## Final evidence pack

程序只读取composer的selected IDs。

原始passage从031 corpus逐字取回；按日期/时间/原始offset排序。

最多8段，总正文预算4000字符；若超预算按composer顺序保留能放入的passage，但至少保留首个selected。

DeepSeek final Judge请求中只含：
- proposition；
- 最终raw-EHR reference。

不会包含：
- requirements；
- Qwen coverage；
- why；
- query；
- 任何上游label/GT。
## 评价

主要终点：raw DeepSeek verdict。

比较：
- B vs A：隔离evidence focusing/composition价值；
- C vs B：隔离新增retrieval价值；
- C vs A：完整前端改造价值。

报告：
- correct / PA / MCC / false-S；
- S/NS/NA recall；
- paired rescue / harm / net；
- 按boundary vs stable分层；
- human vs LLM作者分层；
- B/C reference长度、passage数；
- C新增external passage比例；
- final reason是否实际引用/利用新增证据（描述性）。
## 事前晋级标准

本轮目标是机制screen，不要求显著性。

B或C相对A要被视为“有继续价值”，需同时满足：
1. raw rescue >=3；
2. raw net >=+2；
3. harm <=1；
4. false-S不增加；
5. rescue来自至少2名患者。

若B通过、C不明显优于B：
- 结论偏向evidence focusing/composition为主要瓶颈。

若C相对B再有：
- >=2 rescue；
- net>=+1；
- harm<=1；
则支持missing-evidence retrieval也有独立价值。

若B/C均未过，则不继续扩大该版本。
## 完整性与预算

- cohort、protocol、planner prompt、composer prompt、检索规则、budget在任何065新API结果前冻结；
- GT不进入planner/composer/Judge请求；
- HTTP200不因答案内容重跑；
- API累计hard cap：¥15；
- Qwen/DeepSeek模型固定；
- 0 reserved；
- 不自动commit/push；
- executor verification与独立audit分开。
