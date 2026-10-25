# 031 固定信息组合训练扩充与患者隔离确认

[冻结协议](../../outputs/031_training_expansion_confirmation/protocol_001.md)。只用固定A/B/C/D Logistic；原16训练、新增12扩充/12确认；0 reserved。按完整031累计80元，不能按角色/阶段重置。

当前程序使用独立 `research-verifact-029`，因原C48/API模块导入需要补装duckdb1.5.5；原环境未改。必须通过conda run启动涉及拟合的程序，以取得Windows原生依赖路径。

安全续跑命令（先确认live.lock所记进程已经结束，不能并行启动两个API执行器）：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/resume031.py embedding
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/resume031.py rerank
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/continue031.py
```

`resume031`只按用户明确授权跳过失效account_2，从下一启用账号进行硅基流动BGE；401不记余额耗尽。原始回执及未知预留保留，成功HTTP200永不重发。Judge按原阿里云配置。`continue031`顺序执行主评分、候选角色、八模型确认推理，再连接确认GT；不在确认前读取其GT。

冻结目录/正式结果不覆盖，异常不选优。当前状态在outputs/031.../execution_status.json；费用账本由原始attempts重算。未经另行指令不commit/push、reserved40、032或新参数搜索。
