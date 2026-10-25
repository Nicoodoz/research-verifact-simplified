# 088离线交审入口

这是执行者交接，不是独立审计。本轮在事前规定的P4=F4输入等价条件下停止主实验，不能把未评价的分类差异写成零或等效。

1. `constructor_freeze.json`：首次收费前的代码/协议/示例/模型/提示、源单元SHA；只有四个训练侧示例。
2. `registered_jobs/`和`attempts/`：2个真实P构造请求及回执；返回快照一致、各一次HTTP200。没有源核对、Q构造或主Judge请求。
3. `construction/slot*.json`：原始选择/保留标记。两长例`preserve_full=true`，短例按预登记阈值跳过。不能忽略保留字段手工采用其候选ID。
4. `source_units.json`、`demonstrations.json`、`templates.json`和`source_changes.diff`：24完整原始passage、全部原文未改、三system同SHA；`demonstration_freeze.json`保存构造完成时工件指纹。
5. `decision.json`：无主队列/GT/主请求，质量未评价、P特有机制未测试、成本节省零；不继承087性能。
6. `attempt_ledger.jsonl`和`cost_ledger.json`：输入10298/输出698 token，¥0.0034556/20，未知0。

安全复查：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/088_evidence_preserving_demonstration_compression/test088.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/088_evidence_preserving_demonstration_compression/verify088.py
```

两条均不联网、不写实验产物、不读目标GT。`close088.py`是一次性派生结果生成器，拒绝覆盖已有输出；不要删除冻结文件来重跑。`construct088.py`为收费构造入口，已结项不再调用；`api088.py main`因没有main_freeze会拒绝，不是待补跑任务。

核对器和构造器均非新增医学GT；本次核对器只有合成测试，没有真实源核对调用。原passage既有切段限制保留。087/086工件、reserved、.gitignore和默认系统未变，085A持续暂停。
