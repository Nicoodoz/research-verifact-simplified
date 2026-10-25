# 049：Evidence Decision Utilization

## 目标

048表明查证链能找到支持与反证，也能真实改变Judge，但“只追加原文再判”净收益稀疏。049不再扩大检索范围，固定复用D48内K式证据查证，研究**已经查到的信息怎样参与最终决策**。

Development分层沿用048：原048 screen 4名患者/16条仅作049开发screen；原048 confirmation 4名不同患者/29条保留作规则冻结后的确认。reserved40不参与。

## 阶段0：0 API规则诊断

只使用048 screen已保存的K审计，不新增调用，比较：
- A：明确反证否决。仅当至少一个material requirement被标为contradicted且对应引用逐条有效时，阻止当前U2=Supported，退回同期raw；unaddressed/uncertain/partial不自动否决。
- B：直接查证器。audit核心有效、整体引用有效且audit_label为三分类时，直接采用audit label；否则保留当前U2。
- Hard：历史式严格Gate对照。只有strict Supported才保留U2，否则退raw。仅作负面对照，不晋级。

阶段0不扫描阈值、不组合规则；只决定A/B是否值得作为049正式对照。

## 阶段1：DeepSeek决策接口screen

所有条件共享同一条K式证据查证结果与同一原始EHR evidence pack；不新增full-EHR搜索。

Fresh-B：原E0同期DeepSeek scoring。
E：Evidence-only，同048，把合法引用的external原文追加给DeepSeek，不传查证结论。
C：Requirement→Quote alignment。与E使用完全相同reference，但在user payload新增一个“verification_index”，只包含claim_requirement、原始证据编号、逐字quote；不包含relation、audit_label、GT、U2或旧reason。
R：Relation-aware alignment。与C相同，但允许加入逐要求relation（supported/contradicted/unaddressed/uncertain）；仍不传总体audit_label。

C与R都由同一DeepSeek-V4-Flash-0731重新输出正式三分类verdict/reason/checks/label_scores。主输出使用该次raw verdict；固定λ2只作辅助，不在看到结果后选择raw或λ版本。

另对事前固定8条运行C-control：使用相同引用与相同quotes，但打乱requirement↔quote配对；用于区分“重复强调文字”与“正确语义对齐”。打乱只在同一claim内部进行，且保留原证据编号和quote。

阶段1另事前固定6条Fresh-B与C/R repeat，只诊断最终Judge波动；第一次输出不被repeat覆盖。

## 实时触发、最终决策与screen门槛

049不沿用历史“曾经冲突”作为部署动作。每轮先取得Fresh-B；只有本轮同时满足 raw!=Supported 且固定U2=Supported 才触发A/B/E/C/R。未触发病例最终输出保持Fresh-B的U2。

Baseline-final = Fresh-B U2。
A/B为规则输出；E/C/R触发时用各自新的raw verdict作为最终label，未触发时回Baseline-final。E/C/R的λ2版本只离线报告。

screen晋级有两条预注册通道：
1. accuracy通道：相对Baseline-final净正确>=+2、harm<=1、改善涉及>=2患者、false-S不增加；
2. risk通道：false-S至少减少2、正确数最多损失1、风险改善涉及>=2患者。

C/R若晋级，还需相对E体现增量：正确数至少+1，或在正确数不低于E时false-S至少少1。若C与其打乱配对control表现近似，则不把收益归因为requirement alignment。

最多2个方案进入confirmation；同类方案优先顺序为：净正确更高→false-S更低→额外调用更少。门槛只用于是否投入下一批，不是统计显著性或临床安全线。

## Confirmation

只有screen晋级方案才进入048已预先冻结、且与screen患者完全不重叠的29条confirmation候选。先对29条全部运行Fresh-B，再按本轮Fresh-B动态触发；只对实际触发病例运行D48查证与晋级方法。

确认阶段的方法prompt、索引schema、规则、回退、触发条件不再修改。方法输入不读取GT；预测和所有reason落盘后再连接GT评价。

报告同时给：完整29条路由后最终正确数、实际触发子集转移、患者方向、作者/GT类别、false-S、raw/U0/U2、解释状态和部署调用数。29条不是自然总体benchmark，只是预先冻结的冲突富集确认材料。

## 预算与停止

Screen API保护上限12元；049全任务累计保护上限40元。优先使用DeepSeek-V4-Flash-0731；证据audit沿用冻结Qwen角色，不因DeepSeek便宜而替换已定义的不同角色。

HTTP200不因答案内容重跑；未知结果不自动重发。没有方案过screen门槛则049停止，不运行confirmation。若049结果暴露新的、明确且非重复的机制问题，可按用户本轮授权另立050并执行；050必须独立冻结协议，不能通过修改049门槛“救结果”。

不自动commit/push，不修改.gitignore，不回写历史任务。
