# 系统镜像素材已就绪：待用户保存私有镜像

已在旧无卡实例的**系统盘**`/root/verifact_image`放好完整9B、原环境和105必要运行材料，状态`READY_TO_SAVE_PRIVATE_IMAGE`。原数据盘9B、35B、venv和105原件保留；27B为此前用户单独授权删除，不在本镜像中。没有开GPU、训练、推理、安装/升级依赖或新增API调用。

|系统盘位置|内容|
|---|---|
|`models/qwen3.5-9b`|原始底座四分片、tokenizer、模型/processor配置、revision与来源；约18GiB，revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`|
|`envs/venv103`|原已验证Python3.12环境完整副本，约8GiB；Torch2.8.0+cu128、Transformers5.17.0、Unsloth2026.10.9、PEFT0.21.2等11项一致；基础Miniconda本来就在系统盘|
|`105/bundle`|原30文件冻结运行包，两个196条训练臂、500条完整评价输入、训练/评价/恢复/保存代码及配置、token清单，约32.6MB|
|`105/cost_checkpoint`|旧费用和执行状态快照、累计约束、环境锁与接续说明，不能当作新零费用账本|
|`restore105.py`、`README_IMAGE.md`、`metadata`|新实例恢复入口、操作说明、逐文件SHA、容量与环境/token核验、交付状态|

镜像素材是系统盘上的真实文件；环境和9B没有反向链接到数据盘。45,359个文件/链接已逐项校验；复制后的环境`sys.prefix`及全部11项依赖实际指向系统盘副本，pip check通过，392份训练答案与500个提示token映射一致。未来恢复路径的5项集中检查通过：创建、重复执行、空目录、保留非空目录、拒绝错误旧链接。没有导入Torch/Transformers或加载模型；GPU算子、显存与吞吐仍待后续短检查，105分类实验仍未运行。

实测系统可写配额是**30GiB**，不是用户提到的50G；素材成功放入后还剩约**3.50GiB**。包含原基础系统层在内，完整系统文件约**44.77GiB（48.07GB）**；平台最终镜像大小以控制台统计为准。仅拷贝最终权重，未重复复制`.range`下载临时分片，没有放35B/27B、大wheelhouse、历史optimizer/适配器或额外API/SSH凭据。结果和编译缓存的恢复入口均指向数据盘，避免未来继续挤占系统盘。

**该镜像含105私有临床训练/评价输入，只保存为用户自己的私有镜像。评价GT没有放入，仍在本地用于统计。**

已于**2026-10-28T12:37:14.879054+08:00**同步落盘并调用平台关机入口，随后SSH不可达；尚不能替代控制台“已关机”确认。按[AutoDL官方保存镜像说明](https://www.autodl.com/docs/image/)，确认旧实例已关机后，选择“更多操作→保存镜像”。建议镜像名`verifact_qwen35_9b_105_20261028`；本轮没有替用户保存、共享、释放或重置实例。

新建实例选择此镜像后，优先无卡执行：

```bash
/root/miniconda3/bin/python -B /root/verifact_image/restore105.py
```

该命令恢复标准工作路径并执行CPU核验，保留已有非空目录、结果和真实ledger；不自动训练、不启动GPU、不新增零费用账本。预算/旧区间必须先核对恢复，20元/150分钟不因镜像重置。生成的`start_image105.sh`仍包装冻结start105，并把HF/Torch/Inductor/Triton/CUDA缓存和工作目录放数据盘。

当前这次无卡开机包括先前27B清理与镜像准备，至关机请求估算**¥0.033645**；加历史最低估算，105累计已知约**¥4.503952**，另保留2元共享未知/关机余量。不是平台最终账单，未确认终点不据SSH断开结清。API0；未新增GPU时间。

完整45k文件SHA清单与原回执保留本地私有目录`.local_models/105_brief_supervision/system_image`和镜像`metadata/`。公开阅读依据：[交付摘要](system_image_summary.json) · [镜像说明与恢复入口](../../tasks/105_brief_supervision/image105/README_IMAGE.md)。
