# 043 当前状态

执行完成，执行者核验PASS；独立审计未执行。

55条reserved post-hoc R-B机制样本；该队列不可当新测试集。

DeepSeek普通verdict：A原C48为7/55 S；B定向补证据为20/54 S；C matched context为9/55 S。

严格配对54条：
- B vs A：13 rescue / 0 harm，净+13；患者9正/0负/19平；描述性p=0.000244。
- B vs C：14 rescue / 3 harm，净+11；患者11正/2负/15平；描述性p=0.0127。

B的13条A→B rescue中，12条Qwen reason审计有效，12/12均consistent且grounded，8/12判定新增证据对reason有material贡献。

结论：039定位的目标证据对原DeepSeek Judge确有下游utility；042失败的是通用selector不能识别这些高utility passage，而不是“补证据无效”。

365/365 HTTP200；费用约¥4.832436/¥35。1条DeepSeek B输出缺label_scores、2条Qwen reason audit无效，均未重跑。

入口：report.md · analysis_001/key_results.json · verification_001.json
