# 031独立审计附件

- handoff_snapshot.json / initial_check.json：9161项成果与原交审快照；四份导航指纹也在同步前独立核对。
- audited_files_sha256.json：9160项冻结内容；唯一排除的输出CURRENT_STATUS原值保留在快照。
- independent_check.py / independent_summary.json：原生4513请求/回执、Decimal费用、在途上界、患者哈希划分、科学冻结时序、745缓存reference源绑定；八模型及176内外状态全部重训，主要2000个患者bootstrap点与留一方向独立复算。
- verification.log / verification_summary.json：重跑项目离线核验，25733项通过；包括其余1401条C48候选/打包、精确029特征与全部预测/指标。
- replay_analysis.py / analysis_replay.log / replay_check.json：完整评价重放，13个统计文件字节一致，GT表按ID一致；只允许新GT连接时间及manifest等元信息差别。新目录analysis_audit_001，旧analysis_001不覆盖。
- tests.log / evaluation_tests.log：9项031测试＋15项002评价测试，分别在029隔离环境与原环境通过。
- delivery_checks.json / manifest.json：提交检查和附件指纹。

独立脚本不调用031收费执行器；仅复用冻结028角色模板比对body、029固定学习实现重训。费用及主要混合包络使用独立实现；没有从原raw重建全部EHR或重算全部dense/BM25排名。0新增API、未读取reserved病例。

复查：E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -B reviews/artifacts/031_audit_20260920/independent_check.py
