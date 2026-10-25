# 036 标准对照、reserved40最终验证与论文实验收尾

## 定位与不可更改边界

用户本轮授权使用003原reserved40作最终验证；development已全部暴露，001/002曾有全数据汇总。先补development对照，冻结所有参数后才发送reserved Judge；reserved结果不得用于任何拟合、方法切换或阈值选择。固定U2的λ=2、原API-BGE C48、024 DeepSeek0731和Qwen配置。0新科研特征、0新Gate训练、无reserved选优。历史产物只读。本次累计API硬上限150元，包括失败、未知和在途预留；当前路由Judge阿里云、BGE硅基流动。独立029环境，执行者核验不等于独立审计。

## development标准对照

复用035 run_002所有数值输入、原四折、七方法预测和全development参数。新增022原T/G/M/V，严格原正则、优化器和边界；G原边界[-6,6]是历史标准对照定义，不是扩展Joint的[0,4]搜索。每折仅训练患者拟合，正向/反向Judge迁移使用源Judge折参数，R1复用R0参数。U4只用于核对Joint的决策作用，不搜索新λ。所有对照无论结果如何保留。035 MCC_T迁移有标签变化，继承既有erratum，不改历史报告。

## 最终冻结

固定模型包括035的U0/U2/U2_T/Joint_NLL/Task_T/Robust_T/MCC_T和022的T/G/M/V，后四种使用完整3675条development按原配方拟合；其他沿用035全development参数。Gate仅复用033 gate_A_all40.json，特征12维、原始D/Q score、原threshold和scaler。主线U2；Gate是风险控制，温度是概率分析。标准方法均报告，MCC_T仍探索性历史对照，不按reserved选winner。

## 样本与调用

003固定reserved40全部valid atomic claims，两作者保留，不按GT/难度删选。GT盲读取元数据、claim和EHR，原C48实现与API BGE模型/预算/日期/顺序不改；原VeriFact系统为发布参考而非同证据因果对照。R0全量普通structured B与scoring S；仅S的U0!=S且U2=S调用Qwen。所有离线方法共享S。预先按SHA256('036/repeat/v1:'+patient_id)取前6位患者作R1独立B/S/候选Q；只有在发送任何请求前的全任务保守预测（25%候选、峰值价格、20%余量+3元）<=150才采用6人，否则事前降为4人，再不满足则不做R1。选择与GT、评分、效果无关。R0/R1分开；重复不增加患者样本量。

## 解析、缺失与费用

沿024务实核心字段规则：保留HTTP原文，非核心reason/checks异常记录继续；冲突核心字段为invalid。HTTP200不为答案或格式重跑。无答案通信失败至多3次，未知请求保留上界费用。Q无效/缺失时Gate候选退回U0，报告缺失而不伪造特征。主评分无效无法构造U0，明确覆盖率和缺失ID，主比较共同有效集合，并报全冻结分母missing-as-error敏感性；不冒充完整预测。B失败同理。系统性接口问题、核心异常或预算接近上限停止并保留断点。_2已有031真实401和用户授权跳过，本次记为失效沿用下一启用账号，不声称余额耗尽。BGE限速、真正余额不足顺序换号；不作无意义key探测。

## 评价与统计

002 evaluate/paired_compare，同一分母三分类micro PA/MCC/AC1、混淆矩阵、S/NS/NA召回、false-S（真实non-S被报S）和患者/作者分层。主比较U2-U0、U2-B、U2-O、Gate-U2、U2_T-U2；每个标准对照对U2为辅助。患者cluster bootstrap1000次，共用seed0..999；固定预测重采样，不重新训练，95%区间，多比较不作筛选性显著宣称。NLL/Brier/ECE10及classwise可靠性仅用于有定义概率的方法；不为Gate/B/O伪造概率。R为真实S被救回；H为U0正确non-S被改错；W为原错误non-S又转S，新增false-S=H+W；正确数净变化R-H，与false-S不是同一量。患者正/负/持平和leave-one-patient方向辅助判断集中性。温度不改变标签，不将NLL改善称全面安全或临床校准。

## 收尾

输出机器表、模型/输入/代码指纹、完整回执和累计账本、中文整合报告、论文写作交接稿、图、自检和audit_handoff。报告完成即按用户授权推送，独立审计仍待审。不自动启动037或新的开发。
