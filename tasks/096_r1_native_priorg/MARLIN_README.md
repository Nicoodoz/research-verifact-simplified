# 当前入口：096 AWQ-Marlin

用户已将服务从普通AWQ重启为AWQ-Marlin。本入口替代LIVE_README的旧AWQ运行命令；旧工件全部原样保留为AWQ_DIAGNOSTIC_ONLY，不能作为正式缓存或校准输出。

backend_id：`valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k`。

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin096.py status
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin096.py benchmark --execute
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin096.py formal --execute
```

不要重新运行prepare或live_prepare096来重抽样；准备已冻结。M0内部阶段名P0用于复用085字段解析逻辑，位于新backend独立目录，与旧AWQ P0隔离。样本和body完全相同，新request_id含backend。

HTTP200无论有效与否均不重发。Ctrl+C写STOP_REQUESTED，停止新发送并等待在途落盘；强杀后的未知结果先核对服务空闲。恢复前核对进程和本命名空间锁/STOP_REQUESTED，不能盲删仍运行的锁。旧AWQ锁保留，不影响新namespace。

完成selected Tier全部回执及对账后会打印R1_INFERENCE_DONE。按用户最新要求，先提醒其关闭AutoDL并等待确认，再运行：

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin_offline096.py --gpu-shutdown-confirmed
```

该命令有网络阻断，不访问R1或收费API。随后完成中文报告、结果解读、selfcheck、导航、commit/push。当前默认不升级，.gitignore不改，用户无关文件不夹带提交。

公开输出目录：`outputs/096_r1_native_priorg/valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k/`。
私有响应目录：`.local_models/096_r1_native_priorg/valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k/attempts/`。
