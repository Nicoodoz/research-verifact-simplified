# 047 当前状态

047机制分层多方法screen已执行完成，并按事前门槛停止；不执行已预先冻结的64条confirmation。执行者离线核验PASS；独立审计未执行。

数据边界：044训练材料中的10名已使用development患者按固定hash分为5名screen、5名confirmation，患者不重叠，reserved overlap=0。screen固定24条，confirmation 64条在任何047方法结果出现前已冻结，但未调用。

同期raw verdict结果：
- B DeepSeek：12/24正确，false-S=3。
- J 同E0换Qwen：12/24，3 rescue / 3 harm，净0，false-S不变。
- P 只重排E0：11/24，1 rescue / 2 harm，净−1，false-S +1。
- S 语义选D48证据短窗后交DeepSeek：12/24，2 rescue / 2 harm，净0，false-S −1。

三条候选均未达到预注册门槛，因此无晋级路线。

6条同期baseline repeat中1条发生NS→NA翻转；该病例同时是S的两个rescue之一，因此不能把S全部表面收益归因于新增证据。固定DeepSeek U2正确数B=14/24、P=12/24、S=14/24，也没有显示S带来最终U2增益。

API共119次，119/119 HTTP200；累计usage估算费用约¥2.096631 / screen cap ¥8。完整性核验218项PASS；J与B除模型外请求一致，P只重排原证据，S新增窗口均逐字来自原始EHR。入口：report.md · screen_analysis.json · screen_decision.json · verification_001.json。
