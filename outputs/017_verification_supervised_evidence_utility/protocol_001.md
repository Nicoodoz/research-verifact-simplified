# 017事前方案：由claim verdict产生证据utility弱监督

本方案在任何017收费调用及结果评价前冻结。任务累计上限80元，跨模型／账号／供应商／阶段／失败预留合计；不得修改原数据、原标签或历史回答。

## 科研意义与区别

009/012已定位候选存在但未入包、每note配额、候选前截断等并存损失；013显示广泛扩候选与普通LLM selector有rescue也有harm，均无净收益；010–016还显示同输入Judge波动。因此，先用小、可归因且重复测量的选择干预确认可修复空间，再决定claim级verdict是否足以监督一个低容量证据ranker。不是013 selector提示词v2，也不是重新packing。

医生S/NS/NA只在干预冻结后用于评价correctness变化，不能使原本不是evidence gold的reference或片段变成医学gold。rescue表示该固定Judge在这些输入下更符合原标签，不证明理由正确、内部因果机制或该片段具有独立医学充分性。

## GT盲对象、候选和干预

- 只用003开发序19–30的12名已暴露患者，复用009与016完整冻结材料。按患者×作者，各取固定命名空间`017/GT-blind/patient-author/v1:`的ID哈希前8条，共192条。取样不读GT、既有预测或正确性；013按错误并集选出的231条不作为抽样框。baseline错／对及S/NS/NA覆盖均事后完整报告，不补抽。
- 按患者严格分开：序19–24六人为训练；25–30六人为模型选择。第一阶段两组都产生GT盲干预，但特征、模型、候选数量及选择门槛预先固定。模型选择患者的弱标签不进入训练、标准化或特征选择。之后如果确认，才按原序使用剩余10名全部valid claims；目前仅允许计数元数据，不读其临床正文或GT用于开发。
- C48、BM25/dense列表、BGE分数、原文片段与固定Judge均复用。**宽池W是009/016已真实打过分的A48∪B48∪C48并集**，逐样本冻结，不刷新重排分数。这样避免013已确认的score refresh漂移。W不是013两路top80的更大宽池；历史013 wide结果只作不同范围的历史参照，不声称同池／同期因果对照。
- 三个干预各只换一整段，其他已选证据保留：①C48内同note替换，针对note配额下的替代内容；②C48内跨note替换；③W\C48的候选替换。按incoming BGE降序、outgoing BGE升序、ID稳定破同分，取首个合法配对。不能看GT、旧Judge理由、医生评论或人工锚点找能改对的证据。
- 合法配对保持段数、完整原文、每note≤2、≤16段、正文与记录头≤8000字符；新包长度为原包的90%–110%。使用009原formatter及时间展示顺序，不修复边界、不补写内容、不改变claim或prompt。没有合法替换则原样返回，不重抽病例。另设W＋原BGE贪心selection为容量对照，使用相同8000字符上限（不要求逐字等长）。
- 五条件baseline／同note swap／跨note swap／wide swap／wide relevance，各做两次固定V4-Flash structured判断。temperature=0、max_tokens=2048、thinking=false及原response schema不变。按完整body和重复轮次事前去重；相同条件body共用canonical答案，两轮同body必须独立调用。请求ID哈希交错发送，不选优。已有历史Judge回答仅作历史材料，不替代本轮同期baseline。
- Judge只有原proposition和reference；无GT、作者／source BHC、训练划分、其他模型答案。所有干预对象和完整body先seal，再读取所选192条GT。保留完整请求／回执／usage和无效回答；HTTP200不因格式或截断重跑。

## 第一阶段：headroom门槛（全部满足才继续）

主分析是192条完整固定队列；两轮各用002统一valid-only评价，LLM/human分开、1000次患者cluster bootstrap。不能把两轮当384个独立样本，不做缺失补标签或available-case主结论。

稳定baseline错误／正确：两次baseline标签相同，且均与GT不一致／一致。稳定rescue／harm：原稳定错／对，某swap两次均改对／改错；对不稳定标签另列。每种swap事件和病例并集均报告，wide relevance不计入可学习swap的门槛。

1. 全部逻辑条件覆盖；至少144/192条具有合法swap；至少24条稳定baseline错误和80条稳定正确。否则本次有限筛选证据不足，停止，不补抽。
2. 稳定rescued错误并集≥max(12,ceil(25%×稳定错误数))，来自≥4名患者，LLM/human各≥3条。
3. 其中仅C48内swap可稳定rescue≥6条，覆盖≥3名患者。wide-only新增空间单列，不把候选更多当学会utility。
4. 稳定baseline正确中被任一swap稳定harm的比例≤20%；baseline两次标签翻转率≤15%。必须展示所有harm和病例／类别方向，不仅展示oracle rescue。
5. 训练六患者上至少16个稳定非零utility配对（rescue或harm事件），覆盖≥3名训练患者；确保有最基本低容量拟合信号。无此信号停止，不靠再加prompt或样本挽救。

这是有限干预下的可修复空间／监督充分性筛选，并非证明全局selection上限。报告稳定rescue/稳定错误的分母、与第0轮错误的对应比例、完整样本范围；不存在passage gold，不能精确估计所有错误中“真正有正确证据”的比例。门槛失败即停止017，第二阶段和确认均不执行。

## 第二阶段：一个低容量utility ranker与patient-disjoint选择

仅第一阶段通过后：用训练六患者稳定非零swap的`correct(new)-correct(base)`作为±1配对偏好，预测证据效用差，不预测S/NS/NA。0变化和不稳定比较不作强偏好；保留全部台账与剔除原因。每对正反方向对称加入训练，StandardScaler仅fit训练差向量；固定LogisticRegression(C=0.1,fit_intercept=false,solver=liblinear,random_state=17,max_iter=1000)。不比较tree、不调BGE／Transformer、不搜超参数。

固定8维允许特征：原BGE分数、BGE/dense/BM25倒数排名、log片段长度、claim字母词覆盖率、与保留段的最大词重合、与保留段同note的数量。note ID只用于相等分组，不作数值／类别特征；不使用patient ID、author、source、绝对日期、GT、医生评论、Judge理由或标签分布。训练矩阵严格从8维数值提取；ID仅作审计连接和patient split。

选择器保留baseline或执行一个swap：同池版本只在两个C48内候选动作中选预测效用差最大的正值；宽池版本加上wide swap动作；无正值则保留baseline，平分按固定动作顺序。这个小动作空间与监督记录一致，明确不是全候选任意子集的最优解。

六名模型选择患者96条上比较：C48、同池learned、宽池learned、W＋原selection；两轮结果都从事前完整枚举的真实干预回执按所选动作读取，0新增模型调用。不能从结果中挑某轮或动作。013原wide＋原selection的−5等结果单列历史范围，不混为同期数字。

两learned版本最多选择一个：每轮较C48净≥8、每轮较W原selection净≥5；每轮两个作者净增各≥2；第0轮两作者MCC各提高≥0.03、AC1不降；第0轮≥4/6患者净增，任一患者损失≤2；每作者每类别TP较C48损失≤1，false-S增加≤1。全满足者才是winner，多于一个取第0轮总净增较高者，同分选同池。全部失败则停止，不做v2/v3。

## 冻结后10人确认

只有明确winner，按预定同一训练算法在已暴露12患者的既有稳定配对上重拟合一次，冻结最终权重、标准化、特征、动作空间、C48、Judge、tie规则及版本后，使用剩余10名开发患者全部valid claims一次性确认。模型选择成绩仍来自此前严格六训／六选模型，不用重拟合后的成绩替换。新10人不参与训练／选择／修改，reserved test完全隔离。

新10人比较同期C48与冻结winner，同body事前共享，另每患者／作者各1条固定哈希重复只作波动诊断。确认门槛：总净增≥ceil(2%×N)，两作者各净增≥ceil(1%×n)、MCC各+0.025、AC1不降；≥6/10患者净增，任一损失不超过max(2,ceil(2%×患者n))；每作者每类别TP损失不超过max(1,floor(5%×支持数))且false-S增加≤1。失败即停止，不据新结果改规则。

## 费用与平台

017单任务累计上限80元，包括必要失败／未知预留，所有阶段共用。第一阶段使用缓存候选与真实分数，无新增embedding/rerank；第二阶段离线；确认仅winner通过且实际总预算仍≤80才启动，否则先报告具体估算与申请。不能把三个阶段拆成三个80元。

V4先用硅基流动account_2→_3→_4等启用号池；所有账号明确余额耗尽时保存记录并通知用户，后续转阿里云。超时／503不算余额耗尽，不为测key额外请求。切平台必须核对固定V4非思考配置可用性；若不能保持，不偷偷改thinking／模型或重跑成功回答，报告运行受阻而不是方法失败。同一claim配对跨供应商时须单列限制，不作纯选择因果解释。

## 文献与可主张的贡献

FER已研究verifier反馈的utility，且依赖ground-truth evidence；REPLUG从冻结LM取得检索监督；W-RAG从下游QA构造弱检索标签。utility-aware evidence selection不是首创。017仅检验更具体的条件：个人临床EHR、只有医生claim verdict、无passage-level标注、GT盲有限证据干预、固定Judge、低容量与patient-disjoint选择。只有通过冻结新患者确认，才考虑将这组具体条件下的实证方法作为论文候选；失败同样保存为结果。
