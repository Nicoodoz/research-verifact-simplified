# 034扩展：λ决策边界与置信度实验

**执行及自检完成，尚未独立审计。** 本轮0新增API、0费用，未使用reserved40。未提交或推送。

主报告：[run_001/report.md](run_001/report.md)
指标：[run_001/all_metrics.csv](run_001/all_metrics.csv)
主配对：[run_001/main40/paired.json](run_001/main40/paired.json)
辅助配对：[run_001/supplement/auxiliary_pairs.json](run_001/supplement/auxiliary_pairs.json)
图表：[run_001/figures](run_001/figures)
自检：[run_001/verification.json](run_001/verification.json)

主40人3675条：U2为3012正确、PA81.96%、MCC0.5275、false-S183；U2+T标签不变，NLL1.1806→0.5790，但Brier0.2881→0.2985。
任务λ与稳健λ在所有折返回2；主40人每折仅U2状态满足双约束，未体现稳健选择的独立作用。
联合NLL为3079正确、PA83.78%、MCC0.5367、false-S237；有效λ命中上界4，增益伴随风险增加。
022多类偏置作为辅助对照为3102正确、PA84.41%、MCC0.5516、false-S236，不据此事后改选主方案。

034原三方比较13个文件保持字节不变。执行期间发现并行改名，将扩展代码另存于tasks/034_same_data_comparison/lambda_run_snapshot_001执行，未覆盖外部035目录。完整快照来源、路径修订与冻结哈希均已保存。
