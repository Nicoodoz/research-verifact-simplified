# 010：VeriFact发布系统与009 baseline校准

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/010_verifact_baseline_alignment/report.md)。 独立结论查[审计末尾](../../reviews/010_verifact_baseline_alignment.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

固定009确认的6名开发患者及650条valid atomic claims，两层比较：①提取002对应R1-70B/rater-121发布预测，统一重评分，与009 A48/C48并列；仅作同队列系统参考。②同期用009相同DeepSeek-V4-Flash structured Judge分别核验完整发布reference与冻结C48 reference。原claim、GT、模型、提示与生成设置不变；实际reference内容／长度／格式差异保留并诊断，不冒充纯packaging消融。

实际配置、来源验证、650条映射、两层输入和预估保存于[preparation_001](../../outputs/010_verifact_baseline_alignment/preparation_001/summary.json)。执行前协议见[execution_protocol_001.md](../../outputs/010_verifact_baseline_alignment/execution_protocol_001.md)。预估¥33.05、全任务上限¥40，包含全部尝试与重复；按AGENTS长期授权直接执行，不收费预检。没有新增embedding/rerank/planner、调参、人工改证或新患者。009所有成果与原回答保持冻结。

原发布reference不是医生gold。正文R1-70B的weight别名、辅助结构化步骤等元信息单独保存，不能与硅基流动V4-Flash等同。分别报告LLM/human完整配对、类别、患者、转移、同输入波动及证据层面诊断。

**2026-09-15精简独立审计PASS，可冻结／结项。** 两臂各650条有效预测、24次预设重复均完成；1329次HTTP尝试包含4个402和1个未知结果，合计usage估算/保守预留¥23.4671。没有继续扩展实验。唯一用户主报告为[report.md](../../outputs/010_verifact_baseline_alignment/report.md)，完整入口见[010成果索引](../../outputs/010_verifact_baseline_alignment/README.md)。

主要实现：`prepare_alignment.py`核实release配置、绑定队列/两套输入及预登记重复；`native_stage010.py`复用009已审执行器的独立010副本；`score_alignment.py`仅从回执复用002统一评价；`inspect_references.py`、`additional_reference_diagnostics.py`、`inspect_reference_metadata.py`检查实际证据；`prepare_review010.py`与`extend_review010.py`保存选例；最终解释在`review_notes.json`，由`materialize_review010.py`验证逐字锚点并生成完整案例页；`complete_diagnostics010.py`补充患者/费用/重复和原文条件追溯。没有修改共用评价代码或009实现。

离线重放（使用research-verifact环境，并选**尚不存在**的新输出目录）：

```powershell
python -B tasks/010_verifact_baseline_alignment/verify_alignment.py --output outputs/010_verifact_baseline_alignment/verification_audit_001
```

该入口在进程内阻断网络，核对原始release、冻结配置/body/回执/结果、009所有历史文件，重算指标和案例/补充诊断并逐字节比较，运行150项测试。已有验证见`verification_001`。不要为重放运行`prepare_alignment.py`、`register010.py`或任何live执行器；不要覆盖既有目录。只有依赖版本和完整文本/设置匹配才能复用。

根README、AGENTS、审计文档和无关工作区变化只作版本说明，不作为日常评分阻塞条件；冻结输入/计算材料严格校验。交审版本和未提交修改见[交审说明](../../outputs/010_verifact_baseline_alignment/audit_handoff.md)。执行者不宣布独立PASS，交审后停止修改同批成果。

当前独立结论见[010审计记录](../../reviews/010_verifact_baseline_alignment.md)；原报告、自查及交审材料保留形成时状态，研究限制不因结项消失。
