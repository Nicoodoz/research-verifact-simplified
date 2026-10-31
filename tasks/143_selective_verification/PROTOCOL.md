# 143 support_disagreement：固定缓存送审粗筛

2026-10-31授权后、计算结果前冻结。仅CPU读取指定去正文缓存，不新增训练、GPU/API推理或临床正文审读，不影响142；阶段结果由主执行者统一发布。

## 固定对象与规则

固定134的1817个ID、20名历史评价患者；分别以120 final369、136 claim_repeat为主输出，以107 label_only为辅助。每个主模型都执行且单列，不能挑较好者作为唯一结果。唯一送审规则：`needs_review = (主模型原标签 == Supported and 107原标签 != Supported)`。没有阈值、调参、排序截断或预测标签替换。缺失/无效不能补旧答案；源文件、原标签与原reason均不改。当前去正文缓存无可用reason时明确记缺失，不能借作者或其他模型理由填补。

固定来源：`outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl`、`outputs/136_claim_repeat_transfer/full1817_predictions_sanitized.jsonl`、`.local_models/116_research_cycle/baseline107_selection1817.jsonl`、`.local_models/134_author_baselines/keys.jsonl`。执行记录四份实际SHA及GT/患者/输入hash连接核验；同一1817内计算，不读取其他病例。

## 报告口径

- 全量120、136、107分别保留原生MCC、PA、Gwet AC1、Macro-F1、三类P/R/F1及混淆矩阵、false-S/non-S；送审不改变这些分数。
- 每条主策略单列自动集N/覆盖、原标签的自动集MCC/PA/三类/false-S；同时给残留自动false-S除以全部原non-S和自动集non-S两个分母，以及自动判S假发现率。未定义指标显示NA，不填0。
- 送审人数/命题数、GT分布、拦截的原false-S、被送审的原正确S；按患者、作者、自然400、压力100、新1317、原103的180条分别报告。人工未实际完成，不假设送审后全对，不算虚构的人机最终分数。
- 等工作量参照：在每个主模型原预测S的M条中，不放回随机送审同样n条，其中K条实际false-S，拦截数X服从`Hypergeom(M,K,n)`。报告精确期望nK/M及2.5%—97.5%离散分位区间；这是当前固定队列随机策略参考分布，不是临床安全CI、泛化保证或CP覆盖保证。
- 部署逻辑调用数为`N + 主模型预测S数`，平均`1 + P(主模型S)`；107仅在主模型S时需要追加。不将已缓存的零新增成本冒充部署免费；不把调用数当精确运行时间。

32人是120新增梯度范围；8名内部验证患者曾用于选择且107起点含其43个监督ID，不能当作独立CP校准集。20名评价患者已反复开发使用，100人均有历史暴露，确认40人不自动用于选型。本规则也是基于历史开发认识固定的回顾baseline，不是独立验证或方法创新。普通CP边际集合覆盖不等于本任务的自动接受错误率保证；本次不声称CP/选择性风险控制已建立。

只使用现有`verifact_research.evaluation.evaluate`及既有metrics辅助计算。全量原标签未变，不以自动集和全量MCC的差当作配对原生提升；超几何参照不替代患者级泛化分析。结果无论方向均完整保留，不在本次继续搜索门槛/规则。
