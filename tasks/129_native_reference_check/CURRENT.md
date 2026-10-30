# 129 native_reference_check

已按[固定方案](PROTOCOL.md)完成GPU诊断，比较107与保留的120最终369。选择在读取本诊断输出前完成；128完整500没有增量，未选用。两臂各160条均有效且全部预测NA，原完整reference结果全部复用。见[最终报告](../../outputs/129_native_reference_check/final_report.md)。这是证据移除诊断，不是新训练或新部署方案。

输入为原冻结160条，claim保持、reference显式置空，最大输入377 tokens。107及保留候选的完整reference结果全部复用，不重跑。医生GT不改；空reference下对原GT的变化仅作诊断，不能当新的临床效果成绩。

准备入口：`prepare129.py`。`bind129.py --dry-run`只检查配对；正式绑定必须在读到诊断结果之前完成。运行入口`run129.py --job <job>`复用128的BF16评价代码；`analyze129.py`保留无效和缺失，按原GT分层统计输出变化，不补旧答案。
