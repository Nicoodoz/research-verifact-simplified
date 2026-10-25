# 028 发送前协议：可追溯主张—证据核查

2026-09-19。固定155名额：025的024D 103候选＋026的52候选，16名已暴露development患者。所有非候选沿各自DeepSeek U0，形成879／650／合并1529条全队列评价。不使用reserved40，λ=2、1e−6 floor及tie规则不变。

## 科研依据与区别

已读004、013、015、016最终completion_002、025、026、027正式报告及027审计。004固定事件检查、013表面主谓contract没有稳定净收益；015双方理由仲裁失败，016独立复核仅比普通重复多1条且不及Qwen；025/026的SD为score-only，027显示同输入冲突及高rescue增量不足。028不增加旧清单、不改检索或claim，而是测试**按当前claim动态枚举材料要求，并逐项绑定原证据引文及关系**能否提供额外选择信息；表示有差别不等于有效。

## 唯一两臂及固定放行规则

- 两臂均阿里云deepseek-v4-flash-0731、temperature0、thinking=false、n1、stream=false、max_tokens4096。只见原proposition＋原reference；不见GT、旧D/Q回答、患者ID/作者字段、027错误类型或人工结论。reference原有病历头与去标识身份字段原样保留，不另附隐藏信息。
- repeat：原普通structured prompt/schema，仍200词解释上限；新调用一次。只在verdict=Supported时接受λ改判，否则回U0。不按新答案的NS/NA重新分类，保持可比的候选放行任务。
- trace：输出claim_coverage及动态requirements（最多8项），每项含claim_quote、requirement、evidence_fact、四值relation(supported/contradicted/unaddressed/uncertain)、原reference编号与逐字quote。不得提升情态、排他性、时间范围或额外医学条件，不提供具体病例例子。不要求输出新的S概率或另一个总verdict。
- **唯一确定性gate**：claim_coverage=complete、至少1项、所有项relation=supported，且每项claim_quote存在于原claim、每项至少一条引文存在于其声称的reference编号，才放行为S；其余回原U0。仅允许空白归一化匹配并保存原文偏移，不纠正语义。不存在新训练、调阈值、L2或组合搜索。claim_coverage是模型自报，不是已证明拆解完备性。
- 支持不要求词面完全相同，可接受不增添事实的等义表达；“当前证据未涉及”与明确不一致分开。所有行保留，不能删掉不好核验的要求。列项不改变原atomic claim的医生GT归属。

同生成上限不等于实际等token/等计算量：trace输出可较长，研究比较的是这个表示＋固定聚合方案对普通追加核验的整体增量，不宣称纯结构因果效应。

## 解析、缺失及运行

原HTTP200不重跑；相同重复core key无损折叠，冲突core判invalid；summary/reason/checks非核心轻微异常记录后继续。trace的coverage、claim_quote、relation、evidence ID/quote是core；requirement/evidence_fact文字格式异常单列。core截断/歧义或无法定位引文不能伪造修复。

完整155均进入主系统评价：缺失/invalid/引用不合格时按冻结部署规则退U0，并单列failure；不能把它混成模型语义拒绝。两臂核心共同有效集合另作敏感性，仍报告全155覆盖、ID及主结果。普通解释引用异常遵循024非核心口径；trace引文是放行规则组成部分，额外披露其保守代价和纯关系标签对照计数（只诊断，不新winner）。

请求顺序按ID＋arm哈希交错、GT盲。无答案最多3次尝试，保留未知预算；无成功答案择优。系统模型/接口错误、连续10通信失败或至少10例核心解析失败且滚动100个200的失败率≥10%时停发；少量非核心异常继续。完成后不得因效果改prompt或补成功200。

## 费用

全任务累计80元，包含预检/重试/未知及在途，当前不做无意义预检。发送前官方页https://help.aliyun.com/zh/model-studio/deepseek-v4-flash的**0731快照**北京忙时无缓存输入3、输出9元/百万token，区别于普通别名1/2。继承024/026阿里云同端点与task-local直连，不修改长期路由或OS代理。冻结310个真实body后登记：UTF8字节数＋2000按输入token上界、每次输出4096作保守预留；全部任务预估／实际＋在途均≤80才发送。完整价格、body与模型登记在preparation_001/registry.json。非账单核验。

## 公平评价与预设继续条件

002 valid-only三分类PA/AC1/MCC、S/NS/NA recall、总false-S，候选R/H/W及rescue retention，作者／患者／025和026分开；合并仅描述。1000次患者cluster bootstrap固定历史模型与新输出，无重训。

matched-risk：在新trace固定点的新增false-S预算下，比较①原SD保存概率的全部阈值＋历史正式点；②repeat固定点、U0全拒和U2全放；③完整global非负λ精确状态直到全S。各参照均报告确定性及随机混合期望包络。用GT构造包络只是强参考，不是新方法。合并global使用同一个λ；分队列结果必须保留，不能只挑有利分母。

所有条件须满足才称明显development可行性：

1. 全155都有终结记录；trace核心＋必要引用合格≥95%，否则不能声称实现了可追溯核查。
2. 两队列各保留≥80%原U2 R；合并risk不超过原SD合并risk的75%。
3. trace在同风险下较SD及repeat各自混合参考均≥5R，较完整global混合≥5R；三项患者bootstrap95%下限均>0。
4. 025、026各自相对三个混合参考均正；合并去掉任一患者至少13/16仍对三者同时正。
5. 两作者各自相对SD的净正确非负、总false-S不增；不得靠少数类明显损失取胜。至少两个不同患者有风险错误被修复，不能只靠一个病例。
6. 027原精确冲突组（队列内37＋22条，分别保留）中，候选二分类错误较SD至少少4、较repeat至少少2；原有相反GT对中出现至少两个跨患者的“R放行/风险拒绝”新正确区分对。表示变得不同本身不算成功。

这是一套较高的开发门槛，不是医学安全线。不满足则停止当前语义核查版本，不加检查项、不换复杂模型、不自动029。通过也只报告development可行性并建议后续另行冻结验证，不自动reserved。

## 文本与证据诊断

机器核对全部155的引用、拆解条数、覆盖与原score精确冲突组的实际决策/错误变化。定向深读027既有两对C06/C16、C14/C29，另按两臂不同放行结果及GT转移固定哈希选最多8例；原输出及C48全文可回查。允许少量来源诊断复用既有发布reference，但不把它当完整EHR或gold evidence；任何额外证据不进入主实验，不修改GT，找不到不等于GT错。
