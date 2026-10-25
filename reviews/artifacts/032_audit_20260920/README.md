# 032独立审计附件

- handoff_snapshot.json / initial_check.json：原成果manifest的370项文件初始指纹。
- audited_files_sha256.json：369项冻结内容；只排除输出CURRENT_STATUS，原值保留于快照。
- independent_check.py / independent_summary.json：来源及历史哈希、全部NLI配对重建、权重资产和缓存绑定、135个训练/最终头重放、40个训练内选项复算、一个固定主模型折的重训。脚本复用032分词/网络实现，患者集合、标准化统计、选择规则及绑定由审计脚本另外核对；不称完全独立网络实现。
- check_metrics.py / independent_metrics.json：不用032评价实现，独立计数27组混淆矩阵/PA/MCC/false-S，独立重算主比较1000次患者bootstrap。
- verification.log：实际运行verify032.py的41项最终模型重放。
- replay_check.json：完整002评价重放字节对照，时间元信息除外。新输出位于忽略的outputs/replays/audit032_20260920。
- tests.log / evaluation_tests.log：032任务venv的5项测试与原research-verifact环境15项评价测试。
- delivery_checks.json / manifest.json：交付检查与附件指纹。

复查使用已有research环境DLL及032任务venv：
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -B reviews/artifacts/032_audit_20260920/independent_check.py

完整脚本要求新的评价重放目录；再次运行须为末尾dest指定新路径，不能覆盖原结果。没有重新运行全部NLI编码器推理；验证冻结模型文件、重建配对、配对缓存/袋特征哈希及逐项映射，不能冒称54236个神经输出均重新计算。0API，未下载、修改环境或读取reserved病例。
