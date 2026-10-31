# 当前环境与启动方式（2026-10-31核对）

当前GPU任务为144 native_confidence原500恢复运行：目录verifact144_native_confidence_old500_fixpath、控制64614；原old500目录及0前向失败日志保留。已修复Windows序列化相对路径在Linux的反斜杠问题；仍用原120 final369、BF16/batch1/16384/末位分数，复用232只补481。绝对计算截止18:00:05及180秒保存不重置。145已完成160并回传。共享20元窗口不关机、不释放；141停止、133暂停。

当前为2026-10-31 09:36:01起新增GPU20元窗口，原API80元累计仍为0；之前16元及保持开机等待费用另记。133已暂停，132/137均已完成；415诊断取消且无完整回执。不自动关机或释放。

## 已完成阶段环境记录

以下保留原阶段事实，不覆盖当前授权。[整理前全文](history/2026-10-31_run_environment_before_consolidation.md)。

134两臂1817已完成并回传，135已结束回传，136已完整结束并回传，接续研究可复用32GB RTX4080 SUPER、原9B底座、120 final369和env103，136保存在独立目录verifact136_claim_repeat_full1817；其计算进程已退出。无新权重下载或环境安装。输入token准备使用既有032解释器配合research激活，统计与SSH使用research-verifact-029；135/136复用134编译缓存。原窗口GPU费用持续累计。

前一117夜间窗口已复用同一32GB实例和env103：原9B及107适配器存在、磁盘剩余约96GB、接续时无计算进程。新窗口23:19:14起10小时、GPU15.80元/API80元累计，禁止自动关机。特征缓存仅在私有目录；固定公共标签前缀不含GT。实时显存/吞吐以117运行记录为准，不改116历史。

116周期1已收束：原32GB实例/9B/env103复用，无重装或底座下载。gentle_refresh从107权重及Adam状态固定续训25步，完整输入BF16；最长12220 tokens backward峰值约24.63GiB、余量约6.53GiB。最终模型与完整optimizer/RNG及全部预测已回传.local_models/116_research_cycle/。GPU进程已退出，未发送shutdown；用户保留开机仍计费。周期费用快照与时间见116报告，API0。
115复用同实例、原9B/env103，fresh LoRA与同196/50步；仅导入106的backbone_sum_loss，固定归一360/196，其余沿114已实跑训练/评价循环及107原子checkpoint。最长完整12708 tokens backward、LoRA梯度及显存余量通过；训练日志1893.2秒、500评价971.5秒。最终checkpoint与评价并行回传，私有结果在.local_models/115_label_sum/evidence/。用卡从2026-10-29 18:27:44至2026-10-29 19:26:25，估算¥1.5455/3，API0；没有shutdown或磁盘释放。CPU损失数值核验用032解释器＋research激活，评价用research-verifact-029，无安装或升级。
114复用同一32GB实例、原9B/env103及105分段loss/107滚动checkpoint；从原底座fresh LoRA训练50步，非107/109续训。BF16完整输入、micro1/累积8（两短尾各4）、batch2旧500分组保持。最长12708 tokens backward实测约24.9GiB峰值，LoRA梯度正常；50步训练1885.6秒、500评价963.1秒。最终完整checkpoint与评价并行回传，全部私有结果在.local_models/114_matched_refresh/evidence/。GPU工作18:12:24结束，关键回传18:12:43，任务估算¥1.4252；18:13核实GPU无计算进程，未发送shutdown。CPU token准备使用既有032解释器（主029无tokenizers），统计使用research-verifact-029；无重装、量化或截断。
113同实例/原9B/env103/107适配器，复用106的有界完整标签路径评分函数；每例三次BF16前向、完整JSON+EOS，LM head仅投影答案位置，不保存整词表logits。无训练或新模型权重，原greedy使用缓存，1元全墙钟预算和不自动关机政策保持。
112复用同一32GB实例、原9B/env103，只有原103最终适配器约173MB需要补传。BF16原103 label prompt、768输出上限、贪心解码及parse_label103不变，batch2/正式代表batch1，只补138条；无原9B下载、训练、环境重装或105运行。关键回执及日志在.local_models/112_disagreement_vote/evidence/，计算结束仍遵守不自动关机政策，GPU费用按任务单列。
111完成：复用同实例RTX4080 SUPER 32GB、原Qwen3.5-9B/env103，仅补传本地105最终适配器173MB；无底座下载、重训或环境重装。新增1317×三臂使用原完整作者reference/104 prompt/105 parser及原BF16解码，同分组常规batch2、超12701 tokens者batch1；最长13399 prompt tokens实际通过，context13783容纳完整输入，无截断。全部原始预测与运行记录已回传.local_models/111_half_extension/evidence/。初预算估计剔除一次性编译重复外推，发生的等待、加载、编译与回传仍全计墙钟；没有shutdown或释放。离线统计使用research-verifact-029/scripts/run_research.ps1。

107已在本次RTX5090 32GB完成BF16、micro1、完整输入的两臂LoRA训练与batch2评价；原Python3.12.3/105关键依赖复用，未重装升级。最长backward、辅助LoRA梯度、完整状态恢复和显存/吞吐实测通过。最终适配器、辅助头、完整optimizer与回执已本地回传核验；CPU统计使用research-verifact-029，无需GPU。GPU停止计费状态以107 cost_status与用户确认为准。

103已实际使用独立Python3.12、PyTorch2.8.0+cu128、Transformers5.17.0、Unsloth2026.10.9及PEFT0.21.2环境；补充causal-conv1d1.7.0/ninja1.13.0，未复用096旧vLLM环境。实际依赖锁及验证见[GPU环境](../outputs/103_lora_selection/installed_gpu_with_causal.lock)与[工程记录](../outputs/103_lora_selection/gpu_runtime_amendment.md)。

092研究已经完成。以下是复查/复现说明，不授权新训练、收费调用、部署或安装。环境实测记录形成于2026-09-27；本次只核对文档与既有记录，未重新探测包版本、安装或升级环境。

## 四类环境必须区分

|用途|当前实际环境|声明/证据|
|---|---|---|
|CPU分析、评价、API管理|research-verifact-029，Python3.11.16|根environment.yml；本次CPU零API自检|
|032/092本地GPU核验器|.local_models/032/venv（继承research），Python3.9.23，RTX3060 Laptop 6GB|environment.local-verifier.yml；本次只读包版本快照|
|092已完成的AutoDL训练|用户venv092，Python3.12.3，RTX4090 24GB|environment.autodl-verifier.yml；用户导出的原始环境记录|
|早期分析及021 BGE|research-verifact历史分析；research/research-bge历史GPU|environment.legacy-analysis.yml与environment.local-bge.yml；按原任务复现|

085的A800/vLLM R1 Judge服务是另一条已完成的实验路线，不是092的编码器训练环境。Casperhansen0.9.2与Valdemardi0.10.1.1分支不混为同一checkpoint；不根据旧部署说明访问现有端口或下载权重。

## CPU统一入口

仓库根目录、pwsh：

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/check_research_environment.py
~~~

该脚本禁网、不读取密钥/患者、不写研究结果；验证激活、优化器与矩阵计算。实际任务用同一wrapper传入已授权的脚本和参数。内部是conda run -n research-verifact-029 python -B；Windows的Conda DLL搜索路径需要激活，不能把未激活绝对python路径的故障等同于SciPy损坏。

实测NumPy2.4.6、SciPy1.17.1、pandas3.0.6、scikit-learn1.9.1、duckdb1.5.5、Matplotlib3.10.8。irrCAC和pypdf未在此主环境安装；旧分析配置保留其依赖，不能混称当前主环境。证据：[CPU检查](maintenance/2026-09-27_sync/cpu_environment.json)、[包清单](maintenance/2026-09-27_sync/cpu_packages.json)。

## 本地GPU入口

现有032 venv设置include-system-site-packages=true，需配合research激活。如下仅查看解释器与torch版本，不加载权重、不训练、不写研究结果：

~~~powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -c "import sys,torch; print(sys.version); print(torch.__version__)"
~~~

GPU分析/推理入口见[092复现说明](../tasks/092_task_adapted_verifier/README.md)，只在有合法私有材料的隔离副本复现。092训练入口已由完成标记阻止默认重跑；模型尺寸直接查看[既有记录](../outputs/092_task_adapted_verifier/model_size.json)，不把会写文件的生成器当只读命令。

本地GPU关键版本为torch2.8.0+cu128、transformers4.56.1、numpy1.26.4、scipy1.13.1、scikit-learn1.6.1、tokenizers0.22.0、sentencepiece0.2.1。云端tokenizers0.22.2、sentencepiece0.2.2、Matplotlib3.10.5，与本地不同；不能声称两个环境逐包一致。权重/输入核验、956条标签数值桥接和12条在线原文部署检查已经完成，但不是跨硬件逐字节一致证明。

## 重建清单与历史环境

environment.yml现在声明CPU主环境，不再声明旧research-verifact。旧清单原样关键依赖保存在environment.legacy-analysis.yml；021专用environment.local-bge.yml仍然是历史BGE配置。新local-verifier/autodl-verifier清单只锁定本次实测的直接关键依赖，不是完整传递锁，也未在空环境安装验证。不要用更新配置直接覆盖一个冻结旧环境。

原模型、tokenizer、权重revision和SHA见各任务manifest。092云端激活缓存未转回，本地E盘junction指向原RTX3060缓存；不能把云端cache_manifest的时长套给本地旧缓存。原文、checkpoint及缓存均保持私有忽略目录。GPU租金未知不代表免费。

旧部署/激活故障详见[同步前历史记录](history/2026-09-27_before_sync/README.md)。只读查结果优先；需要严格重放历史hash时按[复查规则](REPRODUCIBILITY.md)使用对应旧版本。
