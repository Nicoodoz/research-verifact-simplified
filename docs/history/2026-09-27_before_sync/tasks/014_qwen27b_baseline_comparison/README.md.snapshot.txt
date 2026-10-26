# 014：Qwen3.8-27B 固定证据模型比较

**2026-09-16修订定向独立复核PASS，R1/R2关闭，可冻结／结项。** 当前结论见[独立审计末尾](../../reviews/014_qwen27b_baseline_comparison.md)。原研究结果和停止边界不变；下文旧待审措辞保留形成时含义，不自动续跑。

目标：判断开放权重27B模型在现有患者EHR核验上的差距和互补性，是否值得后续研究。不是优化方法实验，也不验证本地量化后的性能。

固定009–010的六名开发患者、650条valid atomic claims；主对照使用010的完整C48 canonical结果，009旧C48只作跨运行敏感性参考。Qwen只替换模型字段，不改原claim、reference、structured prompt、标签或生成参数；不重新调用V4。

运行前协议、费用与精确输入见 `outputs/014_qwen27b_baseline_comparison/protocol_001.md` 和 `preparation_001/`。统一评价沿用002。对照非同期，小差异不归因于纯模型能力；六患者不是独立测试集。原医生标签、证据解释及局部部署可行性分别讨论。

使用Conda `research-verifact`。`prepare014.py`只准备本地材料，`run014.py`会真实计费，`analyze014.py`及`verify014.py`只读回执。单任务40元总上限；从account_2起，不读取进程环境重新启用account_1。成功HTTP回答不因标签、格式或截断重新生成。

当前：执行与断网自查完成，等待独立审计，所有收费调用已停止。650条均有效，费用估算加未知预留¥10.761264（上限¥40，非账单）。Qwen整体接近且值得保留为较小模型研究候选，但人写NA召回明显下降；未证明非劣，不自动开展优化或扩样。

唯一必读[中文主报告](../../outputs/014_qwen27b_baseline_comparison/report.md)；精确范围、版本、费用和复核入口见[审计交接](../../outputs/014_qwen27b_baseline_comparison/audit_handoff.md)。183项断网测试、650份只换模型请求核对、65个内容文件重放通过；12,374个历史文件未变。以上是执行者自查，不是独立审计PASS。

复核命令（输出目录须不存在，不调用API）：

```powershell
python -B tasks/014_qwen27b_baseline_comparison/verify014.py --output outputs/014_qwen27b_baseline_comparison/verification_audit_001
```

## 2026-09-16：审计阻塞执行修订

独立快速审计已核对核心结果，R1/R2复现交付问题已作执行修订，等待定向复核，尚未独立PASS。见[修订说明与新交审版本](../../outputs/014_qwen27b_baseline_comparison/revision_001/README.md)。正常审计/顶层入口更新仅报告指纹变化；计算依赖、原回执、指标与报告继续严格验证。Windows冻结代码字节保护已补齐。联合检查中两个任务各196项断网测试通过，65/60个内容文件重放不变，12项篡改拒绝、39个文件真实检出字节相同，无新增API。历史报告/首次handoff保留原状态，不改写独立审计意见。
