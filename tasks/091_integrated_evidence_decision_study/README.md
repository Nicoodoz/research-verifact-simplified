# 091 综合论文、判定诊断与选择性核验可行性

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/091_integrated_evidence_decision_study/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

任务已完成，新增收费API 0次/0元（本轮硬上限20元）。[主报告](../../outputs/091_integrated_evidence_decision_study/report.md) · [完整中文稿](../../outputs/091_integrated_evidence_decision_study/manuscript_zh.md) · [证据对应](../../outputs/091_integrated_evidence_decision_study/evidence_map.md) · [C可行性](../../outputs/091_integrated_evidence_decision_study/C_feasibility.md)。不自动092，不重启C，不改变默认B或历史后处理。

## 安全零API复核

从仓库根目录运行：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/091_integrated_evidence_decision_study/test091.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/091_integrated_evidence_decision_study/verify091.py
```

verify检查已有源SHA、逐分数重放、独立混淆矩阵算式、类路径守恒、036汇总/085分母、C无GT连接及公开边界。已有selfcheck存在时仅返回重放状态，不覆盖它。需要合法本地090私有输入以完成泄露检查和091私有C盲池；缺失时不要自动调用API或凭公开摘要重建临床文本。执行者自检不是独立外部审计。

## 一次性生成顺序与边界

`diagnose091.py` → `c_materials091.py` → `support091.py` → `repeat091.py` → `render091.py`。生成器使用独占写入，已结项后不要当日常重放命令重复运行。人工稿件与主报告以本目录代码生成的表和原正式报告为依据，不通过生成脚本改写旧任务。

B仅使用090全242条及指定078/082/086缓存；主解释集合为四臂common-core自然167/压力65，完整分母及raw自身有效另存。A的036仅引用汇总，不载入reserved个体数据。C只有一次GT盲数值—单位盘点与软件原型，17条/8患者、4缺口/3患者，材料gate未满足，分类实测未执行。`selective091.py`提供动作和同k margin控制函数，不联网、不重标GT。

新临床原文仅在已忽略`outputs/replays/091_integrated_evidence_decision_study/`。Git交付ID、哈希、标签/分数、聚合结果与稿件；不改.gitignore、不提交原始输入/回执或凭据。`finish091.py`只做本任务状态与交付指纹检查，不启动模型。
