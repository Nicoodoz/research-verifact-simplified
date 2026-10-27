# 103：微调模型选型与小规模可训练性验证

第一阶段完成，状态 **READY_FOR_GPU**；等待用户提供实例连接。推荐9B＋3.6-35B-A3B，保留3.8-27B近邻；80GB卡备用9B＋3.8分支。102保持封存。当前没有GPU训练结果，也不授权全量训练。

- [正式中文报告](../../outputs/103_lora_selection/report.md)、[API与GPU准备清单](../../outputs/103_lora_selection/gpu_plan.json)
- [数据/方法协议](protocol.md)、[历史与官方依据](method_notes.md)
- [输出容量修正](label_capacity_amendment.md)、[纯标签格式敏感性](format_sensitivity.md)
- [GPU资源核算](resource_advisory.md)、[完整启动/恢复/关机命令](GPU_RUNBOOK.md)

prepare103.py冻结患者/面板/训练数据；runtime103.py等为已完成API执行的历史入口，不自动重跑。analyze103.py及format_sensitivity103.py保留严格主结果和评分后敏感性。所有API费用累计27.518576元（无缓存目录价保守账），不重置余额。病例正文和完整请求/回执均在私有忽略目录。

GPU代码为gpu_worker103.py、gpu_plan_after_probe103.py、gpu_bridge_check103.py、gpu_lifecycle103.py、install_gpu.sh与run_gpu.sh；依赖见requirements_gpu.lock。真正加载、编译、预跑、训练、峰值显存和吞吐须收到实例后才能验证。已准备两个私有传输包，无权重下载、无实例购买、无GPU计费。
