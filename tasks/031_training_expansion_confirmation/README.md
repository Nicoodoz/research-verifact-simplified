# 031 固定信息组合训练扩充与患者隔离确认

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/031_training_expansion_confirmation/report.md)。 独立结论查[审计末尾](../../reviews/031_training_expansion_confirmation.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

执行、评价、中文报告和执行者自检完成，待独立审计。

- [唯一主报告](../../outputs/031_training_expansion_confirmation/report.md)
- [当前状态](../../outputs/031_training_expansion_confirmation/CURRENT_STATUS.md)
- [冻结协议](../../outputs/031_training_expansion_confirmation/protocol_001.md)
- [交审与安全离线复查](../../outputs/031_training_expansion_confirmation/audit_handoff.md)

固定029 A/B/C/D Logistic、训练内80%阈值及λ2；原16人、新增12扩充/12确认；API-BGE C48、阿里云各角色原配置。费用及未知预留37.70924338/80元。没有确认明显扩充或新增核查信息收益，停止本版本。

日常只读复查（新目录、禁网、0 API、0拟合）：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/offline_verify031.py --output verification_audit_001
```

必须通过独立环境的conda run取得Windows原生依赖路径。主环境不改。reliable_continue031.py是本次恢复的历史入口，使用任务账号授权及IO修订；任务已完成，不要以收费runner代替离线复查。旧resume/continue/workflow及失败日志均保留，不重复启动。

科学冻结见analysis_contract_001/execution_freeze_001；未改prompt、特征、λ、Logistic或阈值目标。不commit/push、reserved40或自动032。
