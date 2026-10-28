# 105无卡准备：READY_FOR_GPU

**代码、固定数据和既有资源已就位；下一次原实例GPU开机后可直接进入短检查与正式队列。没有加载9B/optimizer、模型前向、训练、105预测、收费API、CUDA编译或整套依赖重装；没有创建/克隆/释放实例、切换GPU或新增磁盘。** 实验结论尚未产生。

原104的196条（S83/NS62/NA51，40训练患者）、selection20的400自然＋NS/NA各50、共同新模板、两轮50步/392次消费、分段loss、greedy384及继续标准全部不变。评价GT只留本地；云端500条输入字段逐条检查，无GT、paper_r1或评价标签文件。训练两臂字节与原104完全一致。

|实际完成|依据|
|---|---|
|同103环境复用|Python3.12.3及11项关键依赖metadata全部匹配，pip check通过；未安装或升级依赖|
|同9B原始底座|revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`；全部四个约19.3GB分片8MiB流式SHA匹配103清单，必要小文件一致，原目录无adapter|
|无卡容量|0.5CPU/2GiB，无GPU设备；最终预检峰值约177.4MiB；已有磁盘空闲150.2GiB|
|真实token与答案|tokenizers0.23.3逐一复核392份答案映射及500个完整prompt SHA，与本地0.22.2冻结结果一致；无Torch/Transformers导入|
|独立105目录|`/root/autodl-tmp/verifact105`；103的venv、权重和成果不覆盖，原权重只读核验|
|最小包|30文件/5,614,161bytes，排除评价GT；原v1包与50文件freeze保留，本次工程修订另存映射|
|恢复及启动|wrapper/bash语法、所有运行Python语法、四个CLI路径/参数通过；历史报价dry-run和无GPU拒绝启动测试通过，账本不变；本地6项核心CPU测试与新增关机分派回归测试通过|

修复了实际影响执行的工程缺口：大文件一次性读取改为流式SHA；无卡检查改为tokenizer/Jinja；v1同步包中本地评价键不再上云；新增统一入口、保存manifest和跨阶段预算检查。还发现平台关机文件无执行头，Python直接执行发生ENOEXEC；已保留首次失败并修复为兼容shell调用，修复同时进入GPU守卫。**没有改变科学方法或清洗评价样本。**

当前权重：`/root/autodl-tmp/verifact103/models/qwen3.5-9b`；Python：`/root/autodl-tmp/verifact103/venv103/bin/python`。固定队列为短GPU gate→`label_only`→`evidence_brief`→`base_judge`/`label_only`/`evidence_brief`各500评价→保存→关机。GT回本地统计，不进入推理请求。

下一阶段唯一启动命令（先由用户以GPU模式开启原实例，填入实际报价和平台确认的无卡停机时间）：

```bash
bash /root/autodl-tmp/verifact105/start105.sh --gpu-hourly <实际GPU元每小时> --previous-end <停机Unix秒或带时区ISO时间>
```

这条命令不会开机或切换GPU。云端`budget/ledger.json`是唯一累计账本；前段未结算会拒绝开训。每次重启也不能重置账本。日志`run105.log`、守卫`budget/watchdog_gpu.log`、结果/检查点`results/`。详见[GPU交接](../../tasks/105_brief_supervision/GPU_HANDOFF.md)。

**费用与关机：** 容器PID1开机代理时间为2026-10-28T09:41:10.230000+08:00，修复后关机请求为2026-10-28T10:14:08.078942+08:00；按[官方无卡目录价¥0.1/小时](https://api.autodl.com/docs/save_money/)估算，截至请求累计**¥0.054940**，API/新增磁盘0。平台账单未能读取，代理时间不能冒充平台计费明细。[按量计费规则](https://api.autodl.com/docs/price/)的实际停机终点仍待核；保留2元异常/关机余量，原20元硬上限与18元运行线不变。历史同卡6.98元仅用于dry-run：剩余约2.406小时、约16.79元，不代表下一次实际报价或实测速度。

**10:14:08已通过修复后的守卫请求平台关机，随后SSH会话失效；未取得控制台“已关机”状态或最终脚本回执，关机状态记为REQUESTED_UNCONFIRMED。需要用户在控制台确认原实例已关机；若仍运行请直接关闭，保留实例与磁盘，并记录实际停机时间/费用。不能把SSH断开当作关机成功，也没有据此结清active区间。**

仍待GPU短检查：实际Unsloth/PEFT/CUDA/BF16路径与算子、最长完整训练前后向/LoRA梯度、显存、最长推理批次及完整384输出的KV/平均吞吐。当前无卡通过不证明这些项目或分类收益已经通过；若实际完整任务不符合预算，保存固定任务并停止，不改样本/方法。

工件：[就绪状态](ready_for_gpu.json) · [无卡自检](nogpu_selfcheck.json) · [权重/环境/token回执](nogpu_preflight.json) · [内存/无导入回执](nogpu_process_receipt.json) · [启动检查](nogpu_handoff_checks.json) · [新包清单](sync_nogpu_manifest.json) · [工程修订](nogpu_engineering_amendment.json) · [执行队列](execution_queue.json) · [费用](nogpu_cost_summary.json) · [未结算主账本快照](compute_ledger_snapshot.json) · [关机状态](nogpu_shutdown_status.json)。原[本地阶段报告](report.md)及[原freeze](preparation_freeze.json)保持历史含义；当前入口以本报告和GPU交接为准。
