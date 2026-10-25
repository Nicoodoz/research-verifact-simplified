# 035 当前状态

状态：执行与自检完成，0 API、未用reserved40；尚未独立审计。

主结论：lambda与置信度尺度可解耦。预定Task/Robust规则在16/16个患者外折中均保留lambda=2；U2+T保持分类标签逐条不变，将main40 NLL从1.1806降至0.5790。联合NLL在所有折把有效lambda推到4.0，PA升至83.78%但false-S由183增至237。探索性MCC-only选择lambda在1.35–3.45间漂移，main40 PA提高但false-S增加，020重复轮次方向不稳。

run_001为预定六方法正式结果；run_002加入探索性MCC_T并精确复现六方法。

入口：report.md、run_002/main40/metrics.csv、run_002/main40/paired.json、parameter_summary.csv、verification_001.json。
