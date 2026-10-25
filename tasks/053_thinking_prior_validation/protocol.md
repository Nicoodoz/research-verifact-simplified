# 053：Thinking Scoring Prior-Adjustment Validation

## 目标

分类性能优先。核心评价顺序为：
1. PA / correct；
2. MCC；
3. false-S；
4. Supported / Not Supported / Not Addressed recall；
5. reason-final-label同步仅作次级质量指标，不以牺牲明显分类收益为代价。

052之后保留的主路线为 T-S（thinking-high scoring）。053只比较同一次 T-S 输出上的三个决策规则：
- TS_U2：历史固定 λ=2；
- TS_PriorG：051上冻结的G单Supported偏置 + 051训练患者母体类别比例修正；
- TS_PriorM：051上冻结的M多类偏置 + 同一类别比例修正。

同时保留 N-S U2、036冻结Gate A、原VeriFact发布系统作为对照。N-S与T-S是本轮唯一两路全样本DeepSeek调用。

## 样本

使用全部40名development患者。排除051 screen/confirmation和052的具体claim ID后，每名患者从其已有冻结C48材料中按 SHA256("053/sample/v1:"+proposition_id) 取前6条，共240条。

不按GT、作者、历史正确性、候选状态或模型输出抽样。允许患者此前用于开发；本任务目标是性能开发/内部复制，不把数据隔离当成阻塞条件。仍明确报告证据等级：这是development内部新claim复制，不是外部/保留测试。

证据只复用历史冻结C48/reference，不重新检索。

## 两路Judge

每条claim：
- N-S：deepseek-v4-flash-0731，enable_thinking=false，scoring，max_tokens=2048；
- T-S：同模型，enable_thinking=true，reasoning_effort=high，scoring，max_tokens=8192。

temperature=0，stream=false。输入只含proposition/reference。

## 类别比例修正

G/M参数直接复用052中基于051的16名患者拟合并冻结的参数：
- T-S G theta = 0.1342909508820116；
- T-S M theta = [-0.24744539690775458, -0.7319940680520148]；
并同时对N-S使用对应G/M做公平对照。

参考类别比例只来自051那16名患者在 cohort_master 中全部 valid claim 的标签母体，不使用053 GT：
- Supported 1108；
- Not Supported 100；
- Not Addressed 170。

校准样本比例取051实际训练样本标签计数：
- N-S：48/48/48；
- T-S：48/47/48。

对校准logits追加 log(pi_reference / pi_calibration) 后argmax。参数和比例均在053 API前冻结，053结果不用于调比例或再搜索lambda。

## Gate A

主Gate对照使用036冻结的A Gate配方；fresh N-S满足U0!=S且U2=S时才调用qwen3.8-27b scoring。Gate输入仍是DeepSeek+Qwen的12维score特征。为方便解释，另可离线报告患者外版本，但不把严格隔离设为主约束。

## Final reason

分类标签由上述规则决定。原生T-S verdict与final label一致时可保留原reason作为同步候选；final label被后处理改变时标记 reason_sync=false，不强制重写。分类指标优先，不以reason同步Gate回退分类收益。

## 失败处理

- T-S有合法scores：正常计算三个T-S候选；
- T-S无scores但有合法verdict/reason：raw verdict可保留作诊断；scoring候选采用同期N-S U2作为固定fallback；
- T-S最终content不可用：同样fallback到同期N-S U2；
- 不因结果内容重跑成功HTTP200。

## 费用

阿里云余额约45元。053主调用固定480次DeepSeek；不跑N-V/T-V、不跑全量repeat。Gate Qwen只对fresh U2候选调用。按052实际均价估算核心约9.3元，目标总费用 <=12元，硬cap 15元。发送前按已知历史实际usage做预算检查；若剩余预算不足，不自动扩样本。
