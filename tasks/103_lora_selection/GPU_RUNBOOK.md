# 103 GPU接续说明

2026-10-27实机接续已获用户授权并开始。当前实例使用独立PyTorch2.8.0+cu128环境，实际锁见[installed_gpu_with_causal.lock](../../outputs/103_lora_selection/installed_gpu_with_causal.lock)，调整缘由与算子验证见[GPU工程记录](../../outputs/103_lora_selection/gpu_runtime_amendment.md)。当前已部署实例的单阶段入口为`bash task/run_gpu_live103.sh --model qwen3.5-9b --phase probe`；正式训练加`--phase train --limit 512`或冻结决定的256，恢复另加`--resume`；评价使用`--phase eval --arm native_base`等。不得在当前已部署实例重跑下面历史环境安装或账本init；累计计时从18:15:13开始，守卫持续有效。

以下保留第一阶段交付的原始准备说明；最新实际执行以[实时进度](../../outputs/103_lora_selection/实时进度.md)和上述工程记录为准。

第一阶段完成后暂停READY_FOR_GPU。以下只为用户提供实例后的执行准备，不授权自行租卡；102不恢复。当前依赖已完成Linux/Python3.12解析和hash锁定，GPU算子、速度、峰值显存待实例实测。

## 实例与镜像

优先单张PRO6000 Blackwell 96GB，按量计费，用户参考价6.98元/小时；后备A800 80GB。选择Ubuntu22.04/24.04、Python3.12、CUDA12.8开发镜像，宿主驱动须支持CUDA12.8及该GPU。新建venv103，不复用096 vLLM。PyTorch2.9.1/CUDA12.8、Transformers5.17.0、Unsloth2026.10.9、PEFT0.21.2及全部传递依赖见requirements_gpu.lock。pip check成功后另存实际installed_gpu.lock，GPU加载后再核实算子，不能把依赖解析当GPU验证。

建议CPU≥16核、RAM≥128GB、可用持久磁盘≥320GB（含全专家LoRA恢复检查点及备份，见resource_advisory.md）。BF16大模型全部专家都驻卡，激活3B不等于只存3B；9B约19.3GB、27B约55.6GB、35B约71.9GB权重，另需适配器、optimizer与激活。禁止静默4bit、权重CPU卸载或截断reference。可优先选择自带足够免费磁盘的实例；付费扩容在关机后仍可能计费，须计入60元并在结果备份后安排停止扩容计费，不删除未备份数据。

## 传输与启动（收到连接后由执行者完成）

本地私有包.local_models/103_lora_selection/gpu_bundle.tar.gz含真实数据，不推GitHub。上传至本任务实例/root/autodl-tmp/verifact103并解包；公开代码从本次Git提交取得。环境、模型下载、编译均计入8小时及60元。

```bash
cd /root/autodl-tmp/verifact103
tar -xzf gpu_bundle.tar.gz
# TASK指向仓库的tasks/103_lora_selection，WORK是本任务工作目录。
TASK=/root/autodl-tmp/Research-VeriFact/tasks/103_lora_selection
WORK=/root/autodl-tmp/verifact103
# BILLING_START填写平台本次开机计费开始的Unix秒，不能用训练开始替代。
python3.12 "$TASK/gpu_lifecycle103.py" init --out "$WORK/results" --billing-start "$BILLING_START" --gpu-hourly 6.98 --storage-hourly 0 --storage-fixed 0
nohup python3.12 "$TASK/gpu_lifecycle103.py" watch --out "$WORK/results" > "$WORK/watchdog.log" 2>&1 &
nohup python3.12 "$TASK/gpu_hard_stop103.py" --out "$WORK/results" > "$WORK/hard_deadline.log" 2>&1 &
bash "$TASK/install_gpu.sh" "$WORK"
bash "$TASK/run_gpu.sh" "$WORK" probe
```

存储0元参数仅在已核对免费容量足够时成立，实际单价与开机起点收到实例后填写。watchdog先于安装启动，限时前给本任务worker发送保存信号并备份；只核对本实例machine-id后关机，不影响本地Windows或其他实例。

probe分别从固定原始revision加载；4个optimizer步骤覆盖训练长度p50/p90/p99/最长附近，各有效batch8。保存首次编译与稳定步骤时间、峰值显存、所有训练模块/专家及实际更新。推理测速用固定6条（三类各2），同时核查API/local桥接；9B没有API值则明确缺失。原生本地将4096作为思考上限，达到上限则显式关闭think区再给768最终token，强制边界逐条记录；API内部实现不可独立验证，不宣称逐token等价。label768最终token（统一容量修正，见label_capacity_amendment.md）、禁thinking。两种本地label配置完全相同，微调增量只由它们配对计算。

查看bridge_check.json中的模板、输入长度、格式及标签差异后再继续。scale_decision按实测token/s和生成耗时，先为两个候选各180×3对照留足25%余量，再选择各512或各256；两种规模都无法容纳则保留资源失败事实，不删对照硬训。

```bash
bash "$TASK/run_gpu.sh" "$WORK" train_eval
```

512训练单轮，在256保存中间检查点，不做中间全套评价。预跑参数不用于正式训练。每64条额外保存恢复状态；续跑自动读取resume.json，保留optimizer、随机数与样本位置。成功的固定测速/桥接答案可验证输入SHA后纳入首次本地评价，不按成绩重发。

## 恢复、保存和停机

同次开机恢复直接重运行相应命令，账本不重置。发生关机再开机时，保留旧账本，用resume动作、平台累计账单与新的BILLING_START接续；prior-cny/prior-seconds不能小于旧记录，另计关机期间存储费用。未接收明确第二阶段连接前不执行这些步骤。

```bash
python3.12 "$TASK/gpu_lifecycle103.py" resume --out "$WORK/results" --billing-start "$BILLING_START" --gpu-hourly 6.98 --prior-cny "$TOTAL_CNY" --prior-seconds "$TOTAL_GPU_SECONDS" --storage-fixed "$OFFLINE_STORAGE_CNY"
nohup python3.12 "$TASK/gpu_lifecycle103.py" watch --out "$WORK/results" > "$WORK/watchdog_resume.log" 2>&1 &
nohup python3.12 "$TASK/gpu_hard_stop103.py" --out "$WORK/results" > "$WORK/hard_deadline_resume.log" 2>&1 &
bash "$TASK/run_gpu.sh" "$WORK" train_eval
# 由执行者先回传结果与adapter并核对SHA；不删除云端未备份数据。
python3.12 "$TASK/gpu_lifecycle103.py" finish --out "$WORK/results"
```

finish写入累计费用估计及关机请求，生成独立tar备份，再调用本实例/usr/bin/shutdown。随后核实控制台已关机和实际账单；不能将发出命令当作计费已停止。指标、bootstrap和报告回本地离线完成；本轮不全量训练、不自动进入下一研究。

独立hard_stop守卫确保额外tar打包缓慢不会拖过费用或8小时硬限：普通守卫先在剩余5分钟请求保存，硬守卫在剩余75秒内再次请求保存，并提前关机。它不删除原始输出或检查点；即使额外归档未完成，已有持久文件仍留在实例磁盘。此工程补充不改变科学输入、训练设置或旧冻结记录。
