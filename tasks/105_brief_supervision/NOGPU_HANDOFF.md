> **历史本地阶段交接，保留用于v1重放。当前无卡准备已完成，请读[GPU_HANDOFF.md](GPU_HANDOFF.md)及[无卡报告](../../outputs/105_brief_supervision/nogpu_report.md)。不得再把下面旧v1包上传：它含本地评价键；实际云端已使用排除评价GT的v2包，继续沿用云端同一账本。**

# 105第二阶段入口：先无卡接续

先读本文件、[protocol.md](protocol.md)、[config.json](config.json)和[本地准备结果](../../outputs/105_brief_supervision/report.md)。105只准备好代码和真实数据；下一阶段不要重选196/500、换prompt/epoch或沿用103预测。原104材料和103代码保持原件。

## 先核对既有实例资源，不创建新磁盘

下一阶段由用户提供/管理实例。当前阶段没有登录AutoDL、开机、租卡或收费API。目标复用103已有持久目录：

- 原始权重：`/root/autodl-tmp/verifact103/models/qwen3.5-9b`。
- Python：`/root/autodl-tmp/verifact103/venv103/bin/python`，Python3.12 / Torch2.8.0+cu128 / Unsloth2026.10.9 / Transformers5.17.0 / PEFT0.21.2。
- 新105工作目录：`/root/autodl-tmp/verifact105`，只使用现有磁盘空间。不得覆盖103文件。

实际路径不存在时先核对用户已有磁盘挂载和103备份；本方案未为下载18GB权重、重建整套环境或新付费磁盘预留费用，不自动购买、扩容或启动下载。权重与环境SHA/版本检查在无卡阶段完成。103 GPU使用tokenizers0.23.3，本地tokenizer-only为0.22.2，所以无卡阶段还会逐条核对392份答案映射和500个prompt token SHA；不能仅凭相同tokenizer.json就假定运行结果相同。

## 最小同步包

本地私有包：`.local_models/105_brief_supervision/sync105.tar.gz`，SHA与字节见`outputs/105_brief_supervision/sync_manifest.json`。包内有完整训练/评价原文，禁止Git或公开链接；不含密钥、模型权重、103适配器或wheelhouse。上传到上述105目录后解包为`bundle/`。包内`manifest.json`逐文件校验，代码按冻结SHA运行，不在线拉取“最新版”。

以下为下一阶段Linux命令，**本地准备阶段未执行**。实际计费起点/单价由平台记录填入，不照抄历史价格。每次重启继续同一个`budget/ledger.json`，不要把初始模板覆盖进去。

```bash
cd /root/autodl-tmp/verifact105
tar -xzf sync105.tar.gz
PY=/root/autodl-tmp/verifact103/venv103/bin/python
TASK=$PWD/bundle/tasks/105_brief_supervision
WORK=$PWD/results
LEDGER=$PWD/budget/ledger.json
MODEL=/root/autodl-tmp/verifact103/models/qwen3.5-9b
# 第一次且账本不存在时才init；已有账本严禁重置。
$PY "$TASK/budget105.py" init --ledger "$LEDGER"
# 无卡是否收费、实际单价与开机计费Unix秒均先核实：
$PY "$TASK/budget105.py" begin --ledger "$LEDGER" --kind nogpu --hourly "$NOGPU_HOURLY" --billing-start "$BILLING_START"
nohup "$PY" "$TASK/budget105.py" watch --ledger "$LEDGER" > watchdog_nogpu.log 2>&1 &
$PY -m pip check
$PY "$TASK/verify105.py" --bundle "$PWD/bundle" --model-dir "$MODEL" --work "$WORK"
```

`verify105`不加载模型或需要CUDA卡，检查包、全部四个基础分片、必要小文件、实际103环境版本、既有空闲磁盘及全部真实token映射。不能用`--metadata-only`冒充无卡实机检查成功；该参数只用于本地同步工程检查。无卡阶段费用计入20元总账；目标控制在1元内。不得为了无卡准备让计费实例长时间闲置。

结束无卡阶段时，记录平台实际计费终点；若通过关机/换模式结束，先发finish，再核实控制台后结算原区间。只发shutdown不是计费结束证明。

```bash
$PY "$TASK/budget105.py" finish --ledger "$LEDGER"
# 实际关机/模式切换确认后，填写平台终点再end；未确认保持active。
$PY "$TASK/budget105.py" end --ledger "$LEDGER" --billing-end "$PLATFORM_END" --platform-confirmed
```

如进程意外退出遗留watchdog.lock、supervisor.lock或gpu_worker.lock，先读PID、`/proc/PID/cmdline`并确认相应105进程已不在运行，再只移除相应本任务锁文件；不要启动重复worker或删除账本/成功回执。

## GPU阶段命令与未完成验证

无卡检查通过后，再按用户提供的GPU模式和实际报价接续。不自动租卡。`cost_estimate.json`的6.98元/小时是103同卡历史值；在相同速度、无卡已花1元的假设下，GPU报价约≤7.07元/小时才能维持18元运行线。A800等不同卡的速度/算子仍待实测，不套用Blackwell吞吐。若完整固定任务不再能在预算内完成，保留缺口，不删必要对照。

```bash
# 同一账本上一段已确认结清后；start用实际GPU计费开始时间。
$PY "$TASK/budget105.py" begin --ledger "$LEDGER" --kind gpu --hourly "$GPU_HOURLY" --billing-start "$GPU_BILLING_START"
nohup "$PY" "$TASK/budget105.py" watch --ledger "$LEDGER" > watchdog_gpu.log 2>&1 &
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8 MAX_JOBS=8 TORCHINDUCTOR_COMPILE_THREADS=8
export TORCH_DISABLE_ADDR2LINE=1
nohup "$PY" -u "$TASK/run_all105.py" --bundle "$PWD/bundle" --work "$WORK" --model-dir "$MODEL" --ledger "$LEDGER" > run105.log 2>&1 &
```

两个后台进程独立于Codex等待或SSH会话。supervisor先做GPU gate，再分别从原底座训练label_only和evidence_brief，最后重新加载原底座/两个最终适配器完成三臂500条；恢复重运行同一条命令，自动复用完整检查点和原批次回执。50步/392消费之前不能评价任意epoch适配器。GPU gate只检查真实最长训练反向、小块head与最长完整8行推理批次4-token容量，不更新optimizer、不复用为正式预测。

仍需GPU验证：Unsloth真实backbone输出与PEFT梯度路径、BF16 checkpoint/head数值与显存、causal-conv1d在实际GPU的兼容性、384输出下KV/显存与平均吞吐、完整两臂训练及三臂评价时间和费用。首个正式批次也必须保留，不按成绩重发；输出截断按invalid处理。若发生OOM，不得裁剪病历或偷偷量化；如尚无正式预测，可统一工程调整三臂batch并追加冻结记录，不能只改单臂。已有预测后不改变固定分组来挑成绩。

完成或失败时supervisor请求守卫关机；守卫在18元处独立停机，保留2元延迟/未知余量。结果与两套滚动检查点留既有持久盘，不删除103或未备份105文件。可在GPU评价期间并行回传已完成训练的最终adapter/state；不要为额外打包无限延长GPU计费。任何后续无卡回取仍计同一个20元预算，核实关机和实际账单后才关闭计费区间。

## 回本地评价

取回`results/`、budget账本/停机记录并核对SHA，临床输出继续私有。用本地research-verifact-029：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/105_brief_supervision/evaluate105.py --results .local_models/105_brief_supervision/results
```

自然400与压力100分别出表，保留完整N与有效覆盖；原作者paper_r1只作历史参照。完整执行不等于晋级通过。具体继续判据已固定，不再搜索epoch、后处理或补充样本。本阶段不提交/推送；后续发布仍需用户明确要求。
