# 105克隆实例：先补环境，不直接开训

2026-10-28用户改用新克隆实例，本次操作约束覆盖旧GPU_HANDOFF中的“原实例执行”建议；科学协议、196/500、模板、答案、两轮训练与评价判据不变。

新实例主机为`autodl-container-jnb93wme4w-cae1e260`，与原实例`autodl-container-19d242bf57-d46bf31e`不同。当前新数据盘119GiB，9B四分片流式SHA通过后，仅删除新实例的35B和27B两个无关目录，空闲约100.45GiB。旧实例没有开机、删除、释放或文件修改。

9B原权重已有并完整，不再迁移或下载：`/root/autodl-tmp/verifact103/models/qwen3.5-9b`。105原冻结包已重新从本地同步，30文件SHA与196/500通过，评价GT未上传；位于`/root/autodl-tmp/verifact105/bundle`。不要再次整盘复制覆盖现有材料。

唯一缺失的必要资产是源实例已验证的`/root/autodl-tmp/verifact103/venv103`，目标同路径目前为空。基础镜像仅Torch/部分依赖存在，缺Unsloth、Transformers、PEFT、tokenizers等；这不是补一个小依赖。遵守用户要求，不在GPU上重装整套环境。

下一步只做一次**官方跨实例选择性拷贝**：旧实例作为只读源，选择`/root/autodl-tmp/verifact103/venv103`，拷贝到新实例相同路径。不要选择模型目录、35B/27B、历史checkpoint或整盘`*`。具体入口见[AutoDL跨实例拷贝](https://www.autodl.com/docs/migrate_instance/)。本轮没有可用的已登录控制台窗口；源实例SSH不可达，没有为了复制启动旧实例。需要控制台操作，不能用重建环境代替迁移。

优先在关机/无卡阶段完成迁移。随后运行冻结`verify105.py`核对精确环境、token映射和输入；原环境完整后再确认剩余GPU时间/费用与短资源实测可覆盖的任务。不要直接调用旧启动命令绕过缺失的preflight。实际克隆账本为新实例`/root/autodl-tmp/verifact105/budget/ledger.json`；旧无卡最低估算及未确认预留已带入，不重置预算。

本次GPU计费以用户确认的11:30、6.98元/小时为准，包含克隆、准备与排障；150分钟累计限额和20元总计算限额继续累计，留2元异常/停机余量。停止不等于额度恢复。最终计费/关机动作见本轮报告与进度：[gpu_clone_report.md](../../outputs/105_brief_supervision/gpu_clone_report.md)、[gpu_live_progress.md](../../outputs/105_brief_supervision/gpu_live_progress.md)。

本轮训练、评价均未开始，不能计算新分类指标或把环境阻塞称为监督方法失败。
