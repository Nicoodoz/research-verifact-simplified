# 096现场执行与恢复

最新入口，替代README旧零API等待步骤；原准备文件原样保留。主协议：outputs/096_r1_native_priorg/live_v1/protocol.md。

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py status
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py benchmark --execute
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py formal --execute
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_analyze096.py
```

benchmark完成后冻结tier，formal不再选样。P0/稳定性失败不继续formal，RUNTIME_TOO_HIGH等待用户。HTTP200位置始终复用，包括invalid。正式完成会立即打印R1_INFERENCE_DONE及对账路径；此时可在AutoDL平台关闭实例，之后所有拟合/统计离线。status不探测网络。省略--execute只dry-run。

进程中断：先确认没有本任务进程仍活动，不盲删run.lock；未取得回执的请求按未知在途，必须服务metrics确认idle才能有限恢复。进程安全退出会清锁，强杀留下锁时人工核对PID。若超冻结4小时停止发送，不自动重置时间窗口。

所有临床请求/原始响应在.local_models/096_r1_native_priorg/live_v1，公开只保存ID/标签/哈希/用量。新token API未开启，GPU租金因小时价和计费起点未知暂不填金额。此轮不改变默认，不恢复旧构造任务。
