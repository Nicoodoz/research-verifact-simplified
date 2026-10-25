# 052：First-tier Same-cohort Validation and Thinking-score Optimization

## 目标

036之后真正有系统性能迹象的第一梯队为 N-V、T-S+U2、T-V。052把它们与两条核心基线 U2、U2+Gate A 放到同一批 claim 上比较，同时只做低容量、患者隔离的 T-S scoring 校准，不再扩 retrieval、packing 或长链条 evidence gate。

## 评价患者与抽样

development 40名患者中，051已使用16名。052评价固定使用其余24名患者；reserved40不参与。每名患者从全部 valid atomic claim 中按 SHA256("052/sample/v1:"+proposition_id) 取前10条，共240条。抽样不读取GT、历史正确性、候选状态或方法输出，因此不是冲突富集或类别均衡样本。

每名患者等量10条，主结果解释为 patient-balanced random development sample，不冒充全claim自然prevalence。另报告样本实际GT组成和author组成。

证据固定复用历史C48：原development16名从019/024冻结输入恢复；其余8名从031冻结materials恢复。052不重新检索、不改reference。

## 四路DeepSeek

每条240 claim均运行同一deepseek-v4-flash-0731：
- N-S：non-thinking scoring；最终可产生raw/U0/U2及N-S专属标准校准；
- N-V：non-thinking ordinary verdict；
- T-S：thinking-high scoring；产生raw/U0/U2及T-S专属标准校准；
- T-V：thinking-high ordinary verdict。

N条件：enable_thinking=false,max_tokens=2048；T条件：enable_thinking=true,reasoning_effort=high,max_tokens=8192；temperature=0,stream=false。四条件claim/reference字节一致。

## Scoring后处理

U2沿历史固定公式：对Supported log-score加2后argmax，不重调。

为检验“thinking本身 vs 更灵活校准”，对N-S和T-S分别拟合相同的两个标准低容量后处理：
- G：仅学习一个Supported常数偏置；
- M：学习Supported与Not Supported两个常数偏置，Not Addressed为0。

完全复用022的NLL、L2正则、边界和L-BFGS-B配方。训练只使用051的16名患者保存的screen+confirmation scoring输出和GT；052的24名患者完全不进入拟合或选择。N-S和T-S各自独立拟合相同配方。052结果不用于重拟合参数。

主要scoring候选：T-S+U2、T-S+G、T-S+M；N-S+G/M为公平对照。

## 选择性thinking组合

不增加API，利用同一批已运行输出固定计算：
- NV→TS-U2：N-V若判Supported，则采用T-S+U2；否则保留N-V。
- NV→TS-G/M：同上，复核输出分别为T-S+G/M。
- NV→TV：N-V若判Supported，则采用T-V；否则保留N-V。

这些组合不把N-V结论写入第二次模型prompt；T-S/T-V是独立同证据调用。

## Gate A患者外重建

仅对本轮fresh N-S满足U0!=Supported且U2=Supported的候选调用qwen3.8-27b scoring，使用与036相同reference和score schema。

为避免development训练泄漏，052不直接使用“全40训练”的036冻结Gate A预测。对每个052评价患者，严格排除该患者，用033保存的其余development患者候选与原A特征配方重建StandardScaler+L2 Logistic(C=.1)。阈值仍按原训练内患者LOPO达到至少80%真R保留的规则确定；然后应用到该患者本轮fresh DeepSeek/Qwen 12维score特征。非候选保持U0，候选通过则S、拒绝则U0。

该结果标为 Gate_A_patient_out，不冒充036原全40训练模型的独立测试成绩。

## 主要评价

所有方法在同240条上报告：correct/PA、MCC、AC1、false-S、S/NS/NA recall、患者方向与author分层。主要比较：
1. 第一梯队各方法 vs U2；
2. 第一梯队各方法 vs Gate_A_patient_out；
3. T-S G/M vs N-S G/M（判断thinking与校准的独立贡献）；
4. selective cascade vs其组成的单模型；
5. 原VeriFact发布系统v1.1.0-rater-121同240条系统级参照。

固定预测做1000次patient-cluster bootstrap。240条为development内部患者隔离/训练隔离评价，不是新的reserved或外部医院测试。

本任务探索有效果就完整报告，不因为某方案未被预注册为“主方法”而隐藏；但052评价数据本身不再用于继续调参或挑新lambda。

## 稳定性与费用

事前按hash固定12条，对N-S/N-V/T-S/T-V各额外repeat一次，仅诊断运行波动，不覆盖首次输出。

DeepSeek主调用960次，repeat48次；Qwen只对fresh N-S U2候选调用。按当前3/9元每百万token的DeepSeek保守忙时估算与Qwen3/12估算，052总保护上限60元（低于项目默认80元）。发送前根据冻结body逐项保守预留；HTTP200不因答案内容重跑，未知结果不自动补发。

不修改历史任务、reserved40、.gitignore；不自动commit/push。
