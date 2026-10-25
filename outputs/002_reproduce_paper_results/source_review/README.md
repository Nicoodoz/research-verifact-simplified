# 正式来源核对附件

这里保存 002 录入论文目标值时的固定来源核对材料，不是一次评价运行。

- `formal_page_07.png`：由仓库现有 `docs/sources/VeriFact.pdf` 的第 7 页渲染，已人工视觉核对 Figure 3 图例、曲线端点与 36 个 PA/MCC 标注值。
- `pdftoppm` 是 Poppler 提供的额外命令行工具，未包含在项目 Conda 环境定义中；只在重新生成本目录的来源核对 PNG 时需要。001–003 的日常脚本与测试不调用它。
- 渲染命令：`pdftoppm -f 7 -l 7 -r 160 -png -singlefile docs/sources/VeriFact.pdf outputs/002_reproduce_paper_results/source_review/formal_page_07`。
- 目标值在首次全量复算之前记录于 `tasks/002_reproduce_paper_results/paper_targets.json`。Figure 3 的标注点对应 claim facts N150 / sentence facts N100；N 的定义与作者固定提交中的 `4_agreement_mcc_plots.py` 相符。
- 本地正式 PDF 共 13 页，未附正式 Supplementary Appendix。2026-09-13 尝试访问 NEJM 正文和 `https://ai.nejm.org/doi/suppl/10.1056/AIdbp2500418/suppl_file/aidbp2500418_appendix.pdf` 均返回 HTTP403；Stanford 实验室公开目录列出论文，但未提供可读取的附录。因此不声称复现了正式 Table S3 全表。
- 作者参考代码分别由 `docs/sources/verifact_upstream_f115d36cb65f/source_manifest.json` 和 `additional_source_manifest.json` 固定 URL、提交和 SHA-256。第二个清单追加脚本 9a；未执行任何下载的作者脚本。

原 PDF、原始 release、001 历史运行均保持不变。Figure 3 横坐标词数从真实 reference 独立计算，未从图片估读数值作为匹配目标。
