# 095 统一B基准与证据锚定最小差异核验

先看[中文总报告](../../outputs/095_anchored_minimal_contrast/report.md)与[当前状态](../../outputs/095_anchored_minimal_contrast/CURRENT_STATUS.md)。当前默认不改；指定候选在构造语义阶段全局停止，不自动运行E/C、扩量、顺序控制或下一任务。

## 不收费的复算

在仓库根目录，使用既有CPU/API环境`research-verifact-029`，无需GPU、权重下载或推理服务：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py verify-public
```

该命令从公开统一预测重算官方PA/MCC/AC1/Macro-F1、类别矩阵及Frozen PriorG，只读取标签/分数，不需要临床原文或API凭据，不覆盖冻结结果。原生输入级复核见`selfcheck095.py`和独立审计脚本，需要本地私有回执与合法数据。不要为了重跑脚本删除历史冻结文件；指标生成脚本有独占写入保护。

## 当前费用与准确断点

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py status
pwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py resume-B
```

后者默认只检查缺口。全量成功后会直接返回`B_COMPLETE_NO_CALLS`；成功但core/raw无效的回答同样不重发。若中断留下真正缺失且本095授权、数据与余额仍成立，恢复命令是：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py resume-B --execute
```

恢复沿原ID哈希顺序，按全部095阶段的同ID/同body成功B排除，绝不只按阶段名找缓存。仍用`.local_models/095/budget.sqlite`，所有旧尝试、未知和在途不清零。总硬限150元，普通首次请求130元，原B阶段80元；指定方法停止后，未用预算可供剩余原B最多25元，仍受同一总限约束，不是拆任务重置预算。

若存在run.lock，先检查是否仍有本任务进程。不要在正在运行时删除锁或同时开第二个执行器。进程确已退出后才能移除本任务的单个陈旧锁；请求/回执不删。原始未知请求继续保留最大费用；普通通信故障只对未成功的逻辑请求有限恢复。持续权限、模型或数据异常不能用假结果补齐。

## 源码与工件

- `cache095.py`：真实请求身份盘点；1885个旧成功B按最早规则选取，包含无效。
- `run095.py`：首版忙时保守计价、SQLite原子预留，历史源码不改。
- `run095_v3.py`、`pricing095_v3.py`：经独立复核的时段目录价与跨阶段B去重；未知/错误始终保留忙时最大bound。v2未用于收费执行，旧代码与问题报告保留。
- `method095.py`：唯一构造/核对及拟定E/C实现；`sourcefix095.py`仅修复来源值跨空白的误拒，不生成新内容。
- `experiment_protocol.md`、`decision_clarification.md`：结果前冻结的300样本、B/E/C、继续条件。600扩量顺序和条件式顺序控制均仅登记、未运行。
- `analyze_baseline095.py`、`metrics095.py`、`repeat_diagnostic095.py`：全ID大表、类别/患者/来源/批次、既有重复及原生→最终路径。
- `cost095.py`、`plot095.py`、`report095.py`、`manuscript095.py`：成本、静态科学图与中文交付。
- `outputs/095_anchored_minimal_contrast/`：公开ID、哈希、分数、指标和抽象来源解释。
- `.local_models/095/`：被既有忽略规则保护的临床输入、append-only原生回执、账本及工作材料；不推送。
- `reviews/095_anchored_minimal_contrast/`：独立阶段与最终复核，自检不冒充审计。

模板与实际C48来自冻结092/094材料。固定主Judge为北京`deepseek-v4-flash-0731`、thinking-high、temperature0、8192；构造/检查为同快照非thinking辅助接口。冻结PriorG常数不重拟合。旧reference分支和模型输出无效分别登记，不以其他模型标签补齐。

## 未运行内容与重启条件

300构造＋117核对完成；95自动拟触发并不等于95个真实合格对照。预检与固定24例来源抽查发现保留时点、并列对象、关系绑定以及实质差异的问题，因此最终E/C调用为0。不是C的分类阴性，也不是E/C与B等效。

重启至少需要统一可部署的事件/限定核对，在独立固定盲来源样本中证实能排除这些错误并保留足够操作量；不能用人工挑好例、更多问题、另一prompt版本或剩余预算自动继续。本轮仅完成已授权范围后提交推送并停止。
