# VeriFact私有系统镜像材料

本目录为原103已验证环境、Qwen3.5-9B原始底座与105冻结运行材料的系统盘副本。原数据盘资产保留。镜像包含私有临床训练/评价输入，供用户自己使用，保存为私有镜像，不共享公开。

## 镜像内有什么

- `/root/verifact_image/models/qwen3.5-9b`：原revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`的四个最终权重分片、tokenizer、模型/processor配置与来源记录。没有重复下载中间分片。
- `/root/verifact_image/envs/venv103`：原已验证Python3.12环境完整副本；依赖不升级、不重装。基础解释器`/root/miniconda3`是原系统已有内容，随系统镜像保留。
- `/root/verifact_image/105/bundle`：原30文件冻结包，两个196条训练臂、500条完整评价输入、配置、token长度/映射、训练/评价/保存/恢复/预算代码。评价GT不在该包，仍保留本地用于统计。
- `/root/verifact_image/105/cost_checkpoint`：费用与执行状态只读快照、105交接说明。用于恢复累计预算，不能作为新零费用账本。
- `/root/verifact_image/metadata`：逐文件SHA清单、容量计划、环境和token核验、最终READY状态。
- `/root/verifact_image/restore105.py`：新实例的路径恢复与CPU核验入口。没有添加自动训练、开GPU、下载模型、定时服务或新的活动费用账本。

35B、27B、历史optimizer/适配器、大wheelhouse、下载缓存及API/SSH凭据没有额外拷入本目录；系统镜像本身仍含原系统内容。

## 新实例怎么用

在AutoDL选择保存的镜像创建实例后，优先用无卡模式执行：

```bash
/root/miniconda3/bin/python -B /root/verifact_image/restore105.py
```

它把标准`/root/autodl-tmp/verifact103`的9B/venv以及`verifact105/bundle`链接至系统镜像资产，不再跨实例下载/搬运权重。原非空目录、已有结果与真实ledger保留；遇到不同的旧链接会拒绝覆盖。完整SHA、精确环境及392份答案/500提示token检查仍执行，结果写数据盘`verifact105/results`。

恢复入口还生成`verifact105/image_environment.sh`与`start_image105.sh`，把Torch/Inductor/Triton/CUDA及HuggingFace缓存放到数据盘`verifact105/cache`，并从数据盘工作目录运行。后续GPU使用`bash /root/autodl-tmp/verifact105/start_image105.sh <原启动参数>`；该包装仍调用冻结start105，不改变训练、prompt或解码设置。没有修改系统bashrc，也不会自动启动任务。

有活动GPU worker时拒绝更改路径。该命令不自动训练、开机、切换GPU或初始化费用账本。105先前费用/时间与未确认预留继续累计，须恢复并核对真实ledger及实际开机价格/时间后再走GPU入口；不能因镜像或新实例把20元/150分钟额度重置。当前105没有训练/预测成绩，原196/500、两轮50步/392消费、loss和判据不变。

GPU驱动、BF16/Unsloth算子、真实显存与吞吐仍需下次GPU短检查。无卡的metadata/token与文件SHA通过不代表GPU训练或分类收益通过。

## 保存镜像

确认`metadata/ready.json`为`READY_TO_SAVE_IMAGE`。按平台要求先关机，在AutoDL控制台原实例“更多操作→保存镜像”，命名可用`verifact_qwen35_9b_105_20261028`。不要选择释放、重置或共享镜像。新建实例只需选择该私有镜像；数据盘用于新结果和检查点。
