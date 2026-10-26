# 034：原 VeriFact、U2 与 U2+A全40 同ID比较

目标：在完全相同的40名development患者、3675条valid atomic claims上，离线比较原论文VeriFact历史发布系统、固定U2和033推荐的A Gate训练策略。

本任务不调用任何API，不重新训练Judge/Gate，不使用reserved40。原VeriFact逐条预测来自002；U2和A全40患者外预测来自033。

主比较使用A_all40的患者外/LOPO预测：每个development患者评价时均不进入对应Gate训练，避免直接报告训练本人结果。

运行：

    python -B tasks/034_same_data_comparison/run034.py
    python -B tasks/034_same_data_comparison/verify034.py

结果入口：outputs/034_same_data_comparison/report.md。
