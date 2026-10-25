# 067：Conservative Requirement-Preserving Evidence Packing

## 研究问题

066已定位：Evidence Oracle修复11个当前错误，其中9个来自“关键passage已在C48、但原final pack未完整选入”，1个来自同一final reference的重组，只有1个需要C48外证据。

067因此只研究：

> 如何从已冻结C48构造更适合核验、同时不丢保护信息的final evidence pack？

不扩大检索，不修改LLM推理方式，不优化PriorG。

## 评价集

使用052自然development样本中T-S有效的236条、24名患者。

固定baseline：
- T-S + Frozen PriorG
- 198/236 correct
- PA 83.8983%
- MCC 0.594609
- false-S 6
- confusion GT rows / Pred cols S,NS,NA:
  - S: 167 / 15 / 5
  - NS: 4 / 7 / 7
  - NA: 2 / 5 / 24

052与066的053不是同一批claim，但仍属于development，不能冒充外部确认。

## C48可重建范围

从历史冻结pipeline中为每条claim选择与其baseline reference文本重合最多的C48版本：
1. 031 retrieval；
2. 020 new10；
3. 009 confirmation；
同重合数按上述顺序打破并列。

236条中预计227条有可重建C48，且baseline final reference的每个passage block都必须能映射回所选corpus；否则整条fallback原reference。

无C48轨迹的9条不调用composer、不改变reference。

## 方法：Conservative Pack

核心原则：
- **原final pack是安全底座，不自由重写。**
- 每条最多新增2个C48 passage。
- 只有“覆盖当前pack缺失的material requirement、反证、时间/限定/完成状态”的passage才允许新增。
- 超过原8000字符body预算时，只能删除被明确判为安全冗余的原baseline passage。
- 任何不能安全完成的修改都fallback原pack。

### GT-blind Qwen pack audit

输入：
- proposition；
- 当前baseline passage IDs；
- 完整C48原始passages。

Qwen输出：
- requirements：1–6个material verification requirements；
- must_keep_baseline：不能删除的baseline IDs；
- additions：最多4个当前baseline外的C48 ID，每项包括 requirement、role、priority、why；
- safe_drop_baseline：只有在空间不足时才可删除的baseline IDs；
- unresolved：当前baseline未充分覆盖的requirements。

role限定：
- direct_support
- direct_contradiction
- temporal
- negation
- certainty
- event_state
- scope
- numeric_or_trend

Qwen不得输出S/NS/NA，不得看到GT、历史预测、PriorG或旧reason。

## 硬保护规则

即使Qwen把baseline passage列为safe_drop，程序仍禁止删除以下passage：
1. Qwen列入must_keep_baseline；
2. 文本包含否定/缺失词：no/not/without/denies/negative/never/none/unable等；
3. 文本包含不确定性/条件词：possible/probable/likely/suspect/concern/if/would/could/may/might等；
4. 文本包含事件状态词：plan/planned/scheduled/ordered/refused/cancelled/pending/consider/to be/completed/performed/done/held/stopped等；
5. 删除后会移除Qwen声明的某material requirement唯一baseline覆盖（若可由audit结构判断）。

因此“safe_drop”只是必要条件，不是充分条件。

## 程序化pack修改

对每条：
1. 从原baseline passage集合开始；
2. additions按priority、输入顺序排序；
3. 最多尝试前2个不同requirement的addition；
4. 若加入后仍<=8000 chars，直接加入；
5. 若超预算，只允许从Qwen safe_drop中删除未受硬保护的baseline passage；
6. 每个addition最多删除2个baseline passage；
7. 若仍无法安全放入，则跳过该addition；
8. 若最终没有addition成功加入，整条reference逐字复用baseline；
9. 若改变，则用真实corpus passage重建reference，保持时间顺序，不把requirements、role或Qwen文字交给Judge。

不允许仅为了“变短”而删除baseline passage。

## Final Judge 与后处理

只对reference真正改变的claim重新调用052同配置：
- DeepSeek V4 Flash
- thinking-high
- scoring
- enable_thinking=true
- reasoning_effort=high
- max_tokens=8192

最终机械套同一个Frozen PriorG：
- G=0.1342909508820116
- 051 reference prior / calibration prior完全不变。

未改变reference的claim直接复用原052 T-S scores和PriorG结果。

## 主要评价

完整236条：
- PA
- MCC
- false-S
- S/NS/NA recall
- paired rescue / harm / net
- 患者级win/loss/tie
- patient-cluster bootstrap ΔPA / ΔMCC / Δfalse-S
- changed pack数量
- additions / drops数量
- 按addition role分析

同时报告T-S raw变化，但最终系统主终点为T-S+Frozen PriorG。

## 事前晋级标准

067只有同时满足才值得继续：
1. paired净正确 >= +3；
2. ΔMCC >= +0.015；
3. false-S <= baseline 6；
4. NS recall下降不超过0.02；
5. NA recall下降不超过0.02；
6. rescue覆盖至少3名患者；
7. patient-level正确数改善患者数 > 恶化患者数。

不在结果后修改prompt、max additions、风险词、drop规则或PriorG。

## 解释边界

- 067方法原则受066 oracle诊断启发，因此不是完全独立发现；
- 但067所有pack决策GT-blind，并在另一批052 claims上冻结执行；
- 仍是development，不是最终外部验证；
- 067不研究full-EHR retrieval，因为066/048/065都表明其当前边际价值较小；
- 0 reserved；
- API hard cap ¥30；
- HTTP200不因答案内容重跑；
- 不自动commit/push。

## 固定失败回退

- Qwen audit HTTP200但结构无效：该claim保持原reference，不重跑。
- reference改变后的T-S HTTP200但核心JSON/label_scores无效：最终分类回退该claim原052 T-S scores + Frozen PriorG，不重跑。
- 非HTTP200按执行器错误停止，不隐式改方法。
