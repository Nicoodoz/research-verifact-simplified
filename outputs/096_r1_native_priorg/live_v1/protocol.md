# 096现场执行修订：跨Judge公平性与PriorG迁移

本协议按用户服务就绪后的完整附件执行，保留此前零API准备快照。起始HEAD为28daf95e9b12270d8089246176023c66c4cf298e。旧构造修复不恢复。

服务只访问用户已建立的127.0.0.1:18000，使用EMPTY。用户报告A80080GB、vLLM0.10.1.1、ModelScope Valdemardi AWQ、deepseek_r1 parser；/models实际验证模型名、路径及20000上下文。远端不可变revision、权重字节、完整启动命令尚未提供，不把ModelScope master当HF固定revision，不声称完整复现原VeriFact。

## 冻结与可识别比较

复用同143条/16患者的051校准请求和052/053配方；自然评价排除其患者和085旧180ID，另排除缺V4 raw、Original或完整请求者。自然面板GT×author比例分层，固定SHA256层内排序，最大余数分配400/600/800嵌套样本。少数类面板NS/NA各50/60/100，类别内保持author比例，独立hash取样，与完整自然800互斥。合格母体7484条/84患者；不按任何模型对错、分数或历史error选样。

B语义、claim/C48、模型、temperature0/top_p1/max_tokens8192冻结；无F4、无GT、无旧reason进入请求。085原生parser复用，P0仅按实际envelope冻结字段路径，不按GT修解析。三类分数为LLM自报分数。所有原始响应本地立即append-only保存；HTTP200即终止该逻辑请求，invalid不重发。通信失败最多三次，总体排空后仅在metrics确认无在途时恢复未知请求；无法确认则暂停。

P0最短1条；P1/P2/P3为2/4/8并发、8/12/16条，稳定后P4为12并发24条；P4对P3吞吐提高至少10%才测试P5=16并发24条。各批次short/medium/long、互斥，全部来自各档共有400条，首次回答计入正式结果。成功率/core有效100%、无length、P90<600秒且不超过上一档3倍、可观测process_start不变化为稳定条件。没有远程OOM日志时明确标为不可观测，不伪造无OOM证明。12/16须比已选稳定档吞吐高至少10%，低档选最高吞吐。

实测requests/min加固定25%时长余量：A143+800+200剩余≤3.5小时选A；否则B143+600+120≤3.5小时选B；否则C143+400+100，若仍>4小时停止。仅按速度选择，之后冻结ID/hash，正式新增发送最长4小时；超时暂停，不追加预算。校准→自然→诊断，每25条保存进度并检查服务；滚动有界异步worker，不改变请求体。正式完成即对账并通知R1_INFERENCE_DONE，之后不再访问GPU。

用户此次明确授权已有实例的上述时长分支，替代旧准备模板中未确认的GPU30/API10建议及2/4并发限制。小时价格、完整实例计费起点和实际租金未知，记录实际推理墙钟和小时价乘数，绝不猜余额或把20元API当GPU限额；不新租、不下载、不购买、不改变SSH。按token新API本次优先零调用，桥接优先缓存。

## 离线分析

GPU结束后才拟合R1 G及评价。同052目标函数、正则0.01、范围[-6,6]、log-score floor1e-6；053 NS/NA/S平局顺序。若R1校准core invalid，用预定共同有效交集，记录缺失并同交集重拟合V4作监督对齐诊断；原V4 Frozen参数不改。reference counts保持1108/100/170，calibration counts按有效训练交集。不使用评价GT拟合。

Natural与diagnostic严格分表。先比较三方raw共同有效，再比较所有分数方法共同有效，完整面板coverage/invalid另列，不用旧结果补R1。原作者、V4raw、R1raw、原V4 PriorG迁移、R1-adapted PriorG、当前V4最终；另列U0/Gonly/prioronly。报告PA/MCC/AC1/Macro-F1/precision/recall/F1/confusion/false-S、救回伤害、类别与患者分布、human/llm。1000次患者cluster bootstrap，报告ΔPA/ΔMCC95%区间，不称独立外部验证、不把区间跨零写成等效。不择优升级默认。
