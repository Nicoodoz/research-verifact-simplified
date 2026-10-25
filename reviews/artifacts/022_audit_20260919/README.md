# 022 独立审计附件

2026-09-19。结论以[独立审计](../../022_competition_aware_support_calibration.md)为准。

- handoff_snapshot.json：同步当前导航前的原交审快照，75项全匹配。
- audited_files_sha256.json：排除7项可变导航后的68项被审材料；后续CURRENT_STATUS不回写原manifest。
- independent_check.py / independent_summary.json：独立公式、数值梯度拟合、患者隔离、分类/概率指标及7,557项历史哈希检查；不导入022计算实现、不读取临床正文，禁止网络。
- replay_summary.json：审计者在全新临时目录实际运行冻结verify022.py的摘要。status保留生成器原有executor字样；独立结论在审计正文。
- tests.log / tests_summary.json：022的12项、002评价15项，27项全部通过。
- initial_hash_check.json：原75项交审哈希检查。

复算独立脚本：在仓库根目录和research-verifact环境运行：

~~~powershell
python -B reviews/artifacts/022_audit_20260919/independent_check.py outputs/replays/022_independent
~~~

使用新的输出目录。该脚本不修改研究成果。正式分析重放见[环境与复查](../../../docs/REPRODUCIBILITY.md)。

首次审计辅助计算曾触发Windows NumPy整数中间乘积溢出；修复为Python整数乘积后全部指标吻合。此修复仅在审计辅助脚本，未改研究实现、参数或结果。
