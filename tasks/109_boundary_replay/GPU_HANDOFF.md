# 109租卡交接：先完成准备，再由用户开卡授权

当前目标状态：**READY_FOR_GPU_RENTAL**。代码、受控候选、107标签模型完整状态、固定选样/续训/500评价及结果打包入口已准备；实际CPU自检和包尺寸以[准备自检](../../outputs/109_boundary_replay/final_selfcheck.json)与[包清单](../../outputs/109_boundary_replay/package_summary.json)为准。此状态不表示真实难例已选完或方法有效，也不是GPU授权。

## 1. 已齐材料与真实未知

- 原107 label_only最终step50/392的适配器173,188,512 bytes及完整训练状态346,671,925 bytes均在本地，来源SHA绑定107最终备份。可以继续模型及AdamW/scheduler/RNG，不需要从原底座重训旧label_only。
- 训练40人的3675池、两512候选及已知缺证/歧义标记已复用。固定首批294个NS/NA请求，之后按实际错误至多补274个S；最终候选若可选则192条/1轮/24步，原107 baseline500直接复用。
- **当前训练池真实9B预测缺失**，所以实际64个错误、64个正确近邻S、保留各类是否足够，要在GPU首阶段后才知道。任何不足按冻结规则停止，不扩池救场。未知未审输入不是认证关系难例；没有隐藏的开卡后大规模人工挑例/重标步骤。
- 新实例镜像名/ID、实际模型权重/环境可用性和当前驱动内核未连接核查，不能猜测。真实GPU加载、显存、吞吐与新192效果也未验证。

## 2. 显存和GPU

**首选RTX5090 32GB，最低按32GB规划；32GB仍须实际门槛。** 107已在该规格成功BF16、micro1、完整输入训练，实测peak allocated26,870,898,688 bytes（约25.03GiB），500条batch2推理24,095,741,952 bytes（约22.44GiB）。本109自然候选集合最长prompt12,701 tokens，所需上下文13,097，与107一致；选样没有按长度截断/过滤。训练仍原micro1/累积8；挖掘用batch1留余量，最后500沿107 batch2和分组。

**不推荐24GB承担此训练**：旧真实训练allocated已超过24GiB，不能为省钱改4bit、offload或缩reference。48GB卡（如A6000/L40S）能提供额外显存余量，但本项目当前没有它们的107/109吞吐和内核实测；不能按5090速度承诺。32GB vGPU也不能只凭名称保证算力/独占/驱动，租后需看实际设备和吞吐；优先选已成功的5090路线。

## 3. 镜像、环境与权重

优先使用之前微调9B时保存的私有镜像。历史107及108新实例上曾实际看到：

|路径|应有内容|
|---|---|
|`/root/verifact_image/models/qwen3.5-9b`|原revision c202236…四分片约19.33GB，tokenizer/config齐全|
|`/root/verifact_image/envs/venv103/bin/python`|Python3.12.3、Torch2.8.0+cu128、Transformers5.17.0、Unsloth2026.10.9、PEFT0.21.2、causal-conv1d1.7.0等|

**本地没有完整19.33GB底座，只有small/tokenizer/index；镜像ID与当前是否还可选待用户平台确认。** 本次不访问AutoDL核查，不自动下载权重。107检查点原在数据盘，不应假定包含在旧镜像，故已放进109私有包。

AutoDL保存/加载镜像恢复的是系统盘，不能据此假定数据盘结果也迁移。[AutoDL镜像说明](https://www.autodl.com/docs/image/) 若找不到旧9B镜像，先告知实际可选镜像/旧镜像是否仍在，不要先开一台空环境等大下载和重建。普通新PyTorch镜像不等于已准备好，届时需另估19.33GB权重与约8.48GB环境迁移时间；不能用DeBERTa的108小环境替代9B环境。

## 4. 磁盘与传输

镜像含模型/环境时，建议**数据盘至少20GiB可用，系统盘至少2GiB可用**；本地准备后D盘仍约66GiB以上空闲（最终实测见resources.json），无需为109准备扩容。远端当前容量/空闲未知，不沿用旧实例数值，租后只读核对。

109私有压缩包约0.49GB，解压约0.58GB，包含一个107最终完整检查点、候选及500原输入、代码/标记；不上传9B大权重。两个滚动109完整状态约1.04GB，最终回传约0.5GB，加编译缓存和日志留余量。编译缓存指向数据盘新工作目录，不覆盖旧环境。模型/环境若不在镜像，需额外约28GB以上材料及空间，不能宣称20GiB仍够；默认不付费扩容，先查缺口。

压缩包路径：`.local_models/109_boundary_replay/boundary_replay109.tar.gz`。实际文件数、字节与manifest SHA见[package_summary](../../outputs/109_boundary_replay/package_summary.json)；源状态单独留在原107目录，不覆盖。

## 5. 耗时与建议预算

|环节|依据|预计|
|---|---|---|
|上传/解包及必要模型/环境检查|本机此前约1.5MB/s上传；实际网络会变|5–12分钟，镜像完备前提|
|补训练池预测|294非S＋实际需要的S≤274，挖掘batch1尚未实测；107 batch2的500原评价实测487.29秒|约12–25分钟，非保证|
|新192续训及检查点|107原392消费/50步实测932.40秒，已含44.83秒checkpoint；本次不重复累加旧保存时间|约8–15分钟，继承状态/新卡需实测|
|完整500评价|107同batch2/相同输入实测8.12分钟|约8–12分钟；异常长输出可能增加|
|新最长backward/加载/最终打包回传|不是完整旧审计，必要工程余量|约5–15分钟|

通常按**45–75分钟**估计，谨慎按**90分钟**规划；不能机械把各范围上界当平均。以用户107历史5090报价2.88元/小时作算术场景，45–90分钟约2.16–4.32元；**不是当前现价**。建议未来GPU硬上限8元、API0，预留等待/保存关机余量。预算建议不构成本轮GPU授权，实际租价与用户批准上限收到后重算；实际吞吐显示无法覆盖整轮就报告缺口，不缩必要评价或改方法。

费用从本次真正开机开始计入，包含等待/上传/检查，不从正式训练重计。按量实例计费依据开关机，进程结束不等于停费；扩容数据盘另计。[AutoDL计费说明](https://www.autodl.com/docs/price/)

## 6. 租好后提供什么、如何接续

准备阶段结束前不要开卡等文献、代码或选样程序。请在决定租卡后提供：**新SSH命令和新密码/密钥方式、实际GPU/显存、小时报价、北京时间开机计费时刻、批准的GPU预算、平台自动关机截止/允许的关机方式、所选镜像名或ID**。无需提供旧SSH密码，不自动购买/唤醒旧实例。

收到新GPU执行授权后，由执行者上传私有包并解压到数据盘，例如`/root/autodl-tmp/verifact109/bundle`。先用镜像9B环境检查（不加载模型）：

```bash
/root/verifact_image/envs/venv103/bin/python /root/autodl-tmp/verifact109/bundle/tasks/109_boundary_replay/run109.py preflight \
  --bundle /root/autodl-tmp/verifact109/bundle \
  --model-dir /root/verifact_image/models/qwen3.5-9b
```

将`SESSION_REQUIRED.template.json`复制到**bundle外**的私有session.json，再按**新授权/实际报价与开机时间**填写：绑定本实例与本包、明确GPU_execution_authorized、cap/API0。不要修改冻结包内的config或模板原件。模板现在为false/null，不能直接启动。随后同一Python执行：

```bash
/root/verifact_image/envs/venv103/bin/python /root/autodl-tmp/verifact109/bundle/tasks/109_boundary_replay/run109.py run \
  --bundle /root/autodl-tmp/verifact109/bundle \
  --model-dir /root/verifact_image/models/qwen3.5-9b \
  --work /root/autodl-tmp/verifact109/results \
  --session /root/autodl-tmp/verifact109/session.json --execute-rented-gpu
```

流程固定：294当前预测→64真实错误与S请求→保护/保留配额检查→一候选24步→原500→`return109.tar.gz`。已保存首回执及已提交训练游标可接续；无效不重发，预算不重置。训练前的GPU门槛按实际最大样本与吞吐检查余量。完成或无继续价值时先保存回传，再依新授权及时停止GPU计费，保留实例/磁盘；脚本退出、归档完成本身不代表平台关机。

GPU结束后在本机用`analyze109.py --bundle <本地gpu_bundle> --work <回传results> --output <比较JSON> --bootstrap`复算共同有效集和患者配对。候选真有价值才向用户提出普通回放归因对照，当前第二臂未授权。**当前仅READY_FOR_GPU_RENTAL，等待租卡和新授权。**
