# 105无卡准备完成后的唯一GPU入口

当前阶段只做无卡准备，未切换GPU、未训练或产生105预测。科学设计继续沿用原protocol/config及196/500冻结材料。实际检查、费用和关机状态见`outputs/105_brief_supervision/nogpu_report.md`。

## 唯一启动命令

下一次由用户以GPU模式启动**原实例**后，在其终端执行一条命令：

```bash
bash /root/autodl-tmp/verifact105/start105.sh --gpu-hourly <控制台实际GPU元每小时> --previous-end <平台确认的上次无卡停机Unix秒或带时区ISO时间>
```

如上段计费已在同一个`budget/ledger.json`确认结清，省略`--previous-end`即可。脚本默认用本次容器PID1开始时间作为开机计时代理，若控制台提供更早的实际计费开始时间，再加`--billing-start <Unix秒或带时区ISO时间>`；不能用训练开始时间代替开机时间。实际报价不得照抄历史6.98元。无卡终点未确认时脚本会拒绝开训，不能用SSH断开推定关机。该命令不租卡、不创建/克隆实例、不切换模式。

入口检查包/路径/原权重预检回执、剩余任务费用、重复worker及旧锁，再建立独立后台费用守卫和supervisor。GPU耗时估计使用尚未完成的训练token和评价ID，恢复不重复已经保存的回答。18元运行线/20元硬上限、API0及不新增磁盘不变；无卡、GPU和重启共用一份账本，不重置历史费用。

## 固定执行队列

1. 短GPU资源检查：最长完整训练答案前向/反向、真实LoRA梯度、小块head、最长8行推理批次4-token容量；不更新optimizer、不作为正式预测。
2. `label_only`从同一9B原始底座训练2轮，50步/392消费。
3. `evidence_brief`重新从相同原始底座训练2轮，50步/392消费。
4. `base_judge`、`label_only`、`evidence_brief`三臂各500条，固定完整prompt、分组与384输出上限。评价GT没有同步到105云端目录，不进入请求；统计回本地完成。
5. 持续保存逐步恢复状态与原始完整批次回执，结束时对105结果和检查点流式生成保存manifest。
6. 成功或失败均请求平台支持的`/usr/bin/shutdown -h now`关机；独立守卫在18元处优先请求停机。保存实例与现有磁盘，不释放、重置或删除数据。最终仍要核实控制台已关机及实际账单。

日志：`/root/autodl-tmp/verifact105/run105.log`；守卫日志在`budget/watchdog_gpu.log`；全部105产物在`results/`，账本在`budget/ledger.json`。恢复仍运行上面同一条命令，不另起队列。若检测到对应105进程仍在运行则拒绝重复启动；已死进程的旧锁只改名留痕。

## 工程修订与仍待实测

原本地v1冻结与同步包保留。无卡阶段只做必要工程修订：SHA按8MiB块流式读取；tokenizer/Jinja检查不导入Torch/Transformers；从云端同步包排除评价GT；补齐单一启动、累计预算和保存关机队列。原196/500、答案、GT、模板、训练配方、loss、解码和继续判据未改变。对应指纹见`nogpu_engineering_amendment.json`与`sync_nogpu_manifest.json`。

GPU尚待验证真实Unsloth/PEFT/BF16梯度路径、算子兼容、显存、384输出的KV容量和平均吞吐。无CUDA在当前无卡阶段是正常状态；没有通过重装Torch/CUDA或编译扩展去消除这一正常现象。不得裁剪病历、偷偷量化、删对照或看成绩改规模。
