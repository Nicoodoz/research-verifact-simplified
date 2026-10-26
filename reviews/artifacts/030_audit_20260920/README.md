# 030独立审计附件

- handoff_snapshot.json / initial_check.json：初始12,373项交审指纹匹配。
- audited_files_sha256.json：排除六份可变现行导航后的12,367项冻结内容；导航原值保留于交审快照。
- independent_check.py / independent_summary.json / independent.log：独立重建全部2,400测试单元的GT盲安排；33个最终模型、222个内外状态抽样重训；全141轮R/H/W检查、11人训练40,000个matched bootstrap点、去重动作波动和来源变化复算。
- verification.log / verification_summary.json：实际重新运行close030.py，293,495项通过，32,688个保存模型状态全量重算；该执行者核查工具与独立脚本互为补充，不能混称两套完全独立实现。
- replay_check.json：六个收尾文件逐字节一致。未重跑全部030训练；独立脚本的重训样本由八个预设bin的rep0首个held及全部fallback模型确定，不按成绩选择。
- tests.log：029独立环境内030的8项测试；evaluation_tests.log：原环境002的15项评价测试。
- delivery_checks.json / manifest.json：提交检查及附件指纹。

复查命令：E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -B reviews/artifacts/030_audit_20260920/independent_check.py

0 API，未新增研究方案；新验证目录为outputs/030_gate_training_stability/audit_verification_001，原closeout_001保留。
