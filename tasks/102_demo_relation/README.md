# 102：demo_relation

102已按用户2026-10-27最新指令最终封存，不补跑；零API、分类效果未检验。原预算停止解释的更正和本次双仓库发布授权见[最终封存说明](../../outputs/102_demo_relation/closure.md)。

本轮完成零费用可行性核查后停止，未进行收费分类。[正式报告](../../outputs/102_demo_relation/report.md) · [方法局限](../../outputs/102_demo_relation/method_review.md)。

- protocol.md：单版方法、500三臂＋24重复、预算及分类判据。
- selector102.py：claim/reference原文窗口操作配对；不访问标签或API。
- preflight102.py：来源检查、真实body构造、token计数、完整费用预测；已冻结，不覆盖原结果。
- test102.py：4项合成测试。
- audit102.py：离线来源、请求、配额、特征、预算复核。
- finish102.py：只生成未执行分类的明确状态、选例变化和零费用账本。

CPU入口为scripts/run_research.ps1；分词复用现有085辅助环境及100的官方0731 tokenizer缓存，无模型权重下载、无包安装。本任务没有付费执行入口或计划任务，不能因jobs.jsonl已准备就自动调用。

所有包含临床全文的教学池、目标和请求只保存于.local_models/102_demo_relation；公开只含ID、SHA、数值及抽象说明。构造真实性与分类有效性分开；不能把未运行的MCC/PA/救回写成零分或阴性结果。未提交/推送，默认系统不变。
