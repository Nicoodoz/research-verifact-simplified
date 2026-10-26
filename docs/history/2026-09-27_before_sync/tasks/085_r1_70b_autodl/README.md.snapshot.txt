# 085 AutoDL/vLLM执行分支

[直接操作说明](AUTODL_HANDOFF.md) · [事前协议](protocol.md) · [离线报告](../../outputs/085_r1_70b_autodl/report_offline.md)

原085A和AWS暂停文件保留，不再执行旧SageMaker入口。精确目标AWQ和官方tokenizer的revision/公开文件哈希在identity_lock.json；它是远端验证标准，不代表远端已部署或已匹配。

- `remote_server.py` / `start_server.sh`：用户远端直接启动vLLM，检查数据盘、缓存、权重内容、版本和实际命令；不租实例。
- `server_manifest.sh`：远端零推理观察实际服务及GPU。
- `provider.py`：仅loopback OpenAI HTTP，不含SSH/AutoDL/AWS逻辑。
- `runner.py dry-run`：本地零网络；A/B分别需显式推理开关及真实manifest。
- `runtime_ledger.py`：GPU小时费用，不能当作20元API额度。
- `evaluate_autodl.py`：正式阶段后才物化R1及复用085A统一评价，V4仅复用084。
- `test_offline.py`、`selfcheck.py`：离线测试/只读历史与冻结核查，非独立审计。

本地环境尚无R1_BASE_URL时，不运行A/B，不伪造预测。正式批量另需用户在看到真实吞吐/费用预测后授权。正式085结项后提交推送，不自动下一研究。
