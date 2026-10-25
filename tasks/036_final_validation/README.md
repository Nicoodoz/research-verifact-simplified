# 036：标准对照、reserved40最终验证与论文实验收尾

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/036_final_validation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

## 正式入口

- [冻结协议](protocol.md)
- [最终模型与重复安排](../../outputs/036_final_validation/final_freeze_001/config.json)
- [整项预算](../../outputs/036_final_validation/final_freeze_001/budget.json)
- 结果完成后：[中文总报告](../../outputs/036_final_validation/report.md)、[论文写作交接稿](../../outputs/036_final_validation/paper_handoff.md)、[交审说明](../../outputs/036_final_validation/audit_handoff.md)。

本次明确授权reserved40，3573条valid atomic claims；预先哈希选4名患者444条作独立重复。任务总费用硬上限150元，仅适用036，不改变长期API政策。原033撤回目录不属于本任务。

## 环境与执行

全部通过`pwsh -NoProfile -File scripts/run_research.ps1 ...`启动，使用`research-verifact-029`，不修改原环境。旧035普通`common`模块与检索模块重名，036离线数值代码通过`numerics036.py`隔离导入。

一次性准备顺序：`development036.py` → `plan036.py` → `materials036.py` → `freeze036.py` → `preflight036.py`。这些入口拒绝覆盖已有目录。`scaffold036.py`仅用于首次生成任务内031派生模块，已有代码不要再次运行。

收费执行（仅任务原授权与累计账本有效，勿作日常复查入口）：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/execute036.py all
```

也可指定`embedding`、`rerank`、`judge`或`peer`，成功HTTP200不重跑，累计费用不重置。未知回执保留预留，不能删除attempt后再跑。若存在live.lock，先确认原进程，不能启动第二执行器。

完成全部请求后依次运行`predict036.py`（GT盲预测封存）、`evaluate036.py`（首度连接reserved GT）、`costs036.py`、`correct_accounting036.py`、`plots036.py`、`final_review036.py`和收尾脚本。不得调换GT连接顺序，不得按结果改变配置。正式费用索引为accounting_002，图为figures_002；初版费用金额未错，仅补正供应商meta中的rerank token统计，旧版保留。

## 人工查看进度

```powershell
Get-Content outputs/036_final_validation/execution_status.json
Get-Content outputs/036_final_validation/execution_stdout_001.log -Tail 12
Get-Content outputs/036_final_validation/execution_stderr_001.log -Tail 12
```

`completed_this_call`是当前阶段数量，不是完整任务百分比。`used_cny`包括已记账及未知费用；另加`inflight_reserved_cny`才是发送时占用。`CALLS_STATUS.json`仅表示API阶段完成；中文报告、自检和审计状态以`CURRENT_STATUS.md`为准。

## 安全离线复查

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/test036.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/verify036.py --output outputs/replays/036_check_001
pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/integrity036.py --output outputs/replays/036_C48_check_002
```

复查目录必须不存在且位于`outputs/replays`。不新增API、不会覆盖正式结果。大文件如采用gzip交付，先按`artifact_packages.json`及`package036.py restore`恢复精确字节，核验原SHA256；未改`.gitignore`。

完整receipt重放和模型/指标核验属于执行者自检。036尚未独立审计，不能称独立PASS。按本轮用户授权，完成后直接推送GitHub，不以推送代替审计。
