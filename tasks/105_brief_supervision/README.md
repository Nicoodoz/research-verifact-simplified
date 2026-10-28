# 105短证据监督：READY_FOR_GPU

比较`label_only`（仅医生标签）与`evidence_brief`（短证据与核验关系监督），保留`base_judge`（同模板未微调9B）。原196条/40训练患者、400自然＋100压力/selection20、两轮50步/392消费、loss和晋级规则不变。没有在无卡阶段加载9B、训练、生成105预测或调用收费API。

**下一阶段只读[GPU_HANDOFF](GPU_HANDOFF.md)，按其中唯一命令启动。** 已完成无卡实机核查、必要同步、依赖/权重流式SHA与全部token一致性验证，实际结果与关机状态见[无卡报告](../../outputs/105_brief_supervision/nogpu_report.md)。科学方案：[protocol](protocol.md) · [config](config.json)。

|入口|作用|
|---|---|
|`start105.sh` / `start_gpu105.py`|唯一GPU启动入口；实际报价、前次停机结算、重复进程和剩余预算检查，独立后台守卫及队列|
|`worker105.py`|短GPU gate→两臂独立原底座训练→三臂固定共同评价；不下载权重或访问API|
|`run_all105.py` / `save105.py`|串行恢复队列，逐步保存，结束或失败保存manifest并请求关机|
|`budget105.py`|无卡/GPU/重启共用20元账本；18元运行线、2元停机预留；兼容平台无执行头关机脚本|
|`verify105.py` / `tokenizer_cpu105.py`|8MiB流式权重SHA，metadata/tokenizer/Jinja无卡检查，不导入Torch/Transformers|
|`data105.py` / `loss105.py`|真实answer和构造位置映射；一次backbone及分块head的分段CE|
|`checkpoint105.py`|完整尾批、optimizer/scheduler/RNG、双滚动槽和原子恢复pointer|
|`evaluate105.py`|取得预测后在本地统计，GT不在云端105运行包或推理请求|
|`package_nogpu105.py`|从固定原材料构建不含评价GT的最小云端包，保留原v1冻结与指纹|

105工作目录为`/root/autodl-tmp/verifact105`，103环境、原权重目录原样复用。私有同步包、临床原文、完整答案和回执均不公开。当前包见`outputs/105_brief_supervision/sync_nogpu_manifest.json`；旧`sync105.tar.gz`只供本地v1重放，含评价键，**不可上传**。当前公共无卡费用快照另存`nogpu_cost_summary.json`，原`cost_ledger.json`保留本地阶段0费用快照；实际跨阶段主账本始终是云端`budget/ledger.json`，不得init重置。

原本地报告及50文件freeze保留；修改过的v1代码/交接原件存于`history/preparation_v1`，工程差异见`nogpu_engineering_amendment.json`。本阶段修复不改变样本、答案、GT、模板、训练配方或评价判据。

GPU尚待：Unsloth/PEFT实际导入、BF16与分段loss梯度、算子/显存、完整384输出的KV与平均吞吐。无卡metadata和小张量测试不能替代这些验证。平台停机确认与最终账单按无卡报告记录，SSH断开不代表关机已确认。
