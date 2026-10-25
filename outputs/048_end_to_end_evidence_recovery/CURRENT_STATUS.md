# 048 当前状态

048 的 GT-blind 端到端证据恢复 screen 已执行完成，并按事前门槛停止；29 条患者隔离 confirmation 不执行。执行者离线 verification PASS；独立审计未执行。

触发母体是044 evaluation中系统可观测的 raw DeepSeek 非Supported、固定U2=Supported 冲突，共76条、8名development患者。固定患者hash后，4名患者16条用于screen，另4名患者29条全部冻结为confirmation；GT不参与触发、患者划分或方法输入。

Screen结果：
- B 原E0：raw 2/16正确；U2 9/16正确。
- K D48内逐要求查证恢复：raw 3/16，1 rescue / 0 harm，净+1；U2 11/16，3 rescue / 1 harm，净+2。
- G 完整eligible EHR高召回查证恢复：raw 3/16，1 / 0，净+1；U2 10/16，2 / 1，净+1。

K/G均未达到预注册的 raw净正确>=+2、至少2个raw rescue且跨>=2患者、raw harm<=1、U2净不降、U2 harm<=1、false-S不增加门槛，因此无晋级方法。

机制信号：
- K改变9/16 reference，G改变8/16；最终DeepSeek显式引用新增编号均为7/16。
- K与G的raw最终标签16/16完全相同；U2仅1条不同。完整EHR G没有显示出超过D48内K的raw增量价值。
- raw verdict运行很稳定：历史044→同期B为0/16变化；6条B repeat与6条G repeat均0次raw变化。
- label_scores/U2明显更不稳定：历史044→同期B有6/16 U2变化；6条B repeat有2条U2变化，G repeat有1条。
- Supported score均值 B=14.38、K=21.56、G=20.31；补证据会明显移动分数，但可同时产生U2 rescue和harm。

API共90次、90/90 HTTP200，usage估算约¥1.657362 / screen cap ¥10。verification 222项PASS。入口：report.md · screen_analysis.json · screen_decision.json · verification_001.json。
