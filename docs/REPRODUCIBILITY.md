# 当前复查与复现入口（2026-09-28）

095研究已结项，含B真实补齐、来源诊断与构造停止；本文是离线复查入口，不自动调用API或开启下一任务。环境见[RUN_ENVIRONMENT](RUN_ENVIRONMENT.md)，各任务的历史入口见[TASK_INDEX](TASK_INDEX.md)。

## 优先只读

先看[095总报告](../outputs/095_anchored_minimal_contrast/report.md)、[统一9065表](../outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl)和[最新稿](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)。零API、无临床原文复算：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py verify-public
```

恢复B的准确入口、同一总账和成功不重发规则见[095 README](../tasks/095_anchored_minimal_contrast/README.md)；完成后恢复命令无新调用。

092历史训练结果可查看[092报告](../outputs/092_task_adapted_verifier/report.md)、[指标](../outputs/092_task_adapted_verifier/metrics.json)、[完整稿](../outputs/092_task_adapted_verifier/manuscript_zh.md)和[完成指纹](../outputs/092_task_adapted_verifier/completion.json)即可。模型权重、原文与私有缓存不在Git，克隆仓库并不提供受许可限制的完整重训材料。

CPU环境检查为：

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/check_research_environment.py
~~~

该入口禁网且不写研究工件。各任务analyze/render/verify/selfcheck名字不保证只读：不少会写固定结果或检查文件。不要以“验证”为理由覆盖已冻结结果。

## 092复算

在独立checkout/副本中携带合法私有输入和十组权重，按[092 README](../tasks/092_task_adapted_verifier/README.md)复算。analyze092、supplement092、write_report092、manuscript092、plots092等会写结果；selfcheck092/final_check092也写检查JSON。当前正式工作区不默认重跑；一次融合已完成，不重新拟合择优。完整训练必须另行授权并使用空的独立输出/模型目录。

旧本地暂停材料在092/local_pause_archive，云端训练完成结果另有manifest；有效训练源码冻结v3不因为导航更新而改变。云端RTX4090与本地RTX3060缓存有浮点差异，不能将本地缓存误作下载的云端激活。部署推理可以从原始文本重新编码，不要求保留整份激活缓存。

## 更早任务的严格重放

协议、报告、审计、来源、计算代码和manifest保持形成时内容。本次更新的是现行导航和环境声明；某些旧manifest把README等导航也登记了SHA。若严格验证涉及这些旧导航，在对应历史commit的隔离checkout运行，或先核对归档原字节；**不得修改旧manifest、放宽哈希或把当前README当当年文件**。

本次修改前导航逐文件原字节在[历史快照](history/2026-09-27_before_sync/README.md)，基准commit ee8060a2b。更早冻结版本由任务manifest/审计记录指定，不能认为ee8060a2b适合所有早期任务。

019–021曾提供scripts/replay_completed_research.py，要求全新outputs/replays目录并禁网；其他任务各有输出/路径限制，按其正式交审说明执行。历史复查使用对应环境：environment.legacy-analysis.yml保留早期包版本，现行environment.yml为029分析环境；不自动升级旧依赖。

## 数据与证据等级

保留原GT、invalid、全部失败/未知回执及缺失分母。全体100患者已暴露，092全部标签使用有明确授权；OOF不是新独立外部测试。原作者同ID、自然/压力面板、raw/score/final及fallback口径分别核对。

执行者自检与独立审计分开；更新README不能将“待审”变成未经执行的PASS。实际独立结论见[审计索引](../reviews/README.md)。本次没有重跑研究结果或验证在线服务权限。
