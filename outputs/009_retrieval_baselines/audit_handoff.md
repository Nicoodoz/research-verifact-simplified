# 009 交审入口：执行修订完成，等待独立复核

主报告：[report.md](report.md)。可选论文设置／数表／相关工作：[paper_draft.md](paper_draft.md)。本入口为执行者交接，不宣布独立审计PASS。

**实际代码基础：** `main`，HEAD=`42d28c4909b901056207c6770e1be733998123cf`。开始时工作区干净，已核对origin/main；结束前再次fetch，具体远端与本地状态记录于[handoff_001.json](handoff_001.json)。009尚未提交。被审版本为该HEAD加清单中的全部未提交文件，不能仅checkout HEAD评审009。

**修改范围：** 新增 `tasks/009_retrieval_baselines/`、`outputs/009_retrieval_baselines/`、`tests/test_retrieval_baselines.py`；只更新根README/AGENTS当前入口（包括同步008已存在的精简独立审计状态）。没有修改.gitignore、原始数据、002评价实现、001–008实验代码／历史run／原始回答、独立审计意见或本地key文件。未提交文件、精确哈希与清单指纹以handoff为准；交审后停止编辑同批成果。

## 重点复核入口

|重点|实际文件|
|---|---|
|执行前授权与方案|[authority_001.json](authority_001.json)、[总协议](execution_protocol_001.md)、[重排漂移修订](execution_amendment_001.md)、[新队列冻结](confirmation_protocol_001.json)|
|当前实际实现|[study009.py](../../tasks/009_retrieval_baselines/study009.py)、[确认构建](../../tasks/009_retrieval_baselines/build_confirmation.py)、[服务调度](../../tasks/009_retrieval_baselines/native_stage.py)、[回执解析](../../tasks/009_retrieval_baselines/io009.py)、[统一评分入口](../../tasks/009_retrieval_baselines/score009.py)|
|可继续使用baseline|[设置](../../tasks/009_retrieval_baselines/baseline_config.json)、[本地接口](../../tasks/009_retrieval_baselines/retrieval_baseline.py)；旧008核心只导入不改写|
|原EHR→索引→候选|[650条准备](confirmation_001/preparation/)、[向量与候选](confirmation_001/candidates/)、[实际Judge输入与缓存](confirmation_001/judge_preparation/)|
|真实服务回执|[live/](live/) 七个固定阶段；无新增planner。dev_embed为登记后的rerank刷新，费用未遗漏|
|主指标和完整性|[confirmation analysis](confirmation_001/analysis_001/metrics.json)、[预测／转移／患者／重复](confirmation_001/analysis_001/)、[全精度数表](synthesis_001/)|
|开发容量及rerank对照|[144条开发结果](development_001/analysis_001/)、[固定24条诊断](development_001/analysis_001/diagnostic_metrics.json)|
|完整案例及锚点|[旧15例](development_001/review_001/semantic_001/)、[新35例](confirmation_001/review_002/semantic_001/)、[定向追溯与追加解释](confirmation_001/targeted_trace_001/interpretation.md)、[预设重复翻转N119](confirmation_001/repeat_followup_001/N119.md)|
|干预与费用|[冻结控制输入](interventions_001/preparation/)、[完整53条件结果](interventions_001/analysis_001/)、[解释限制](interventions_001/interpretation.md)、[总费用](synthesis_001/costs.json)|
|自查|[verification_001](verification_001/verification.json)、[143项断网测试日志](verification_001/tests.log)、[逐请求provider token记录](verification_001/provider_token_accounting.csv)|

可定向检查P081/P058的dense已找到但融合排除，N394分路保留补回临床评估，N430两路前80外，N561/N563模态标题与结果断开，N585字符预算损失，N071先前检查与后期Definity结果，以及N302/N293/N487干预的完整输入与控制。锚点不是医学gold，不据关键词或Judge解释认定因果。共享API重排见过某片段，与该臂候选资格是两个字段。

## 验证范围与已知限制

- 全部650条主确认、三臂均完整；新确认重排38,893配对均有真实分数。同完整Judge请求预先共享canonical，重复仅作诊断。主比较1,303 canonical＋12重复，1次重复翻转；没有补标签或按答案重跑。
- 自查禁网重建了两队列原文切段、向量、各路排名、候选、真实分数、全部2,478个主/开发条件的最终reference/body、缓存、预测及指标。各路排序相同，浮点末位差异量在verification明确记录；输出的预测/评分/锚点/渲染逐字节一致。143项测试通过，仍不等于独立审计。
- 事后干预9例／53条件均有效，52次新发送；18个重复5次翻转。N410无供体移除背景控制；背景不是严格无效安慰剂，部分长度不匹配。人工选证不作为部署性能，原主预测不变。
- 总费用估算¥18.08218167，包含全部阶段和8次402恢复（无答案、费用0），40元总上限未超；rerank usage来自meta而非顶层usage字段。无账单核验、无不可变模型权重标识。
- 开发最初补算12个跨日重排哨兵发现最大差0.001374，按协议刷新全开发候选并集，不混旧新分数；费用包含两个批次。最初评分输出路径错误在保存内容后报错，修复后17内容文件重放一致，完成记录见 `development_001/analysis_completion.json`，不影响主指标。旧记录不覆盖。
- C48仅暂定实用baseline；C−A增益很小，未证明稳定优越或非劣性。35例初筛后补读全部8个原NS翻转属事后类别覆盖，非随机总体错误率。原医生标签和原文语境的潜在差异保持不确定，未查看reserved test病例。

离线复核命令（新输出目录须不存在）：

```powershell
conda activate research-verifact
python -B tasks/009_retrieval_baselines/verify009.py --output outputs/009_retrieval_baselines/verification_audit_local
```

日常审计文档/根入口修改不阻断重放；冻结输入、配置、计算代码、原回执和输出指纹仍严格检查。审核请以handoff清单固定版本，期间执行者不继续修改。
