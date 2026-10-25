# 029 离线运行入口

**当前：36组条件全部完成；用户追加授权收尾后，中文主报告及执行者核验已完成，待独立审计。** 最初只启动后台运行的约定及run_001原始RUN_STATUS保持形成时状态。

唯一必读：[中文主报告](report.md)。另见[当前状态](CURRENT_STATUS.md)、[交审](audit_handoff.md)、[收尾自检](closeout_001/checks.json)。

- [冻结协议](preparation_001/protocol.md) · [配置](preparation_001/config.json) · [特征定义](preparation_001/feature_schema.json)
- [输入指纹](preparation_001/manifest.json) · [队列核对](preparation_001/cohort_summary.json) · [独立环境版本](preparation_001/environment.json)
- [启动前合成测试](preflight_001/tests.txt)
- [后台启动记录](launch_run_001/launch.json) · [stdout](launch_run_001/stdout.log) · [stderr](launch_run_001/stderr.log)
- [程序实时状态](run_001/execution_status.json)；完成或失败后生成 [RUN_STATUS.md](run_001/RUN_STATUS.md)。尚未完成时不会预写研究结论。

正式机器结果由程序写入 `run_001/patient_OOF/evaluation`、`run_001/025_to_026/evaluation`、`run_001/026_to_025/evaluation`。每个scope下各条件目录保存逐折训练ID、模型、内层OOF及最终阈值。异常时保留现场，查看 `run_001/errors.json`。

全部参数及特征在029真实性能评价前冻结。8主条件＋4质量消融；不自动选winner，不访问reserved40，不调用API，不修改历史结果或原环境，不自动commit/push。
