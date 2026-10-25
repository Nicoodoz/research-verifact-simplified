# 081：GT-blind evidence selection vs GT-aware teacher（首个收费请求前协议）

本任务由用户明确交办；历史066–080协议和结果保持原样。默认收费API全任务累计硬上限¥20，含planner、composer、同期B/U/T Judge、全部重试及未知/在途预留。超过或无法合理估算则先确认；不拆阶段重置。任务结束不commit/push、不启动082、不改`.gitignore`、不使用reserved。

## 冻结对象与资料级别

- 评价患者固定为078的24名development患者，PriorG参数来源患者隔离；不是独立新测试。候选C48、原final reference、proposition、患者/作者来自历史**无GT输入**。要求原包逐span映射为同一C48的passage ID；映射不完整者在抽样之前一律不eligible。
- 严格eligible池每患者至少8条。按每患者`SHA256("081/sample/v1:"+proposition_id)`取4条Stage1；优先此前盲输入文件中未出现的claim，不足才取已暴露claim。Stage2在同一排序后再取4条，不与Stage1重合，且仅在gate/预算允许时执行。抽样不看GT、任何模型预测或oracle名单；暴露和来源manifest冻结，后续另核066–069逐ID交叠，不换样本。
- 在U planner/composer和U final pack全96条冻结之前，U代码路径只读白名单中的blind source/C48/corpus及自身回执，绝不打开human GT、历史预测、正确性、066 oracle/GT构造需求等文件。阶段先后和文件依赖自检必须验证此约束。之后才join GT并构建T；T只有附加的`clinician_label`信息，其余候选、模型、prompt、温度、最大输出、schema、formatter与U相同。
- B为相同claim的历史final reference原文，重呼同期T-S Judge；旧B exact-body若存在，仅作同体波动分析。U/T最终Judge均只见不变proposition与真实EHR passage组成的reference，不见标签、planner/composer结果/理由或目标判别元信息。

## Selector与证据预算

- 延用066两阶段Qwen3.8-27B non-thinking，`temperature=0`、JSON输出：planner列1–6个完整命题核验requirements；composer从该病例**全部冻结C48**（最多48条）选1–16个真实passage ID，附审计字段。U/T的system文本相同，均说明可选`clinician_label`存在时可用；U用户payload无此字段，T用户payload仅额外此字段。composer同样只额外传GT；U/T的planner差异为各自输出，不作手工干预。
- U/T formatter完全相同：沿009现有C48 final pack约束，最多16条、每note最多2条、完整展示行body最多8000字符、同日同类别同文本去重、不截断单条passage、最终按date/time/note/start展示。composer所列顺序、formatter保留/跳过及展示顺序均登记。B也必须满足同约束；无效/空选择按原包B作为两臂共同事前fallback，不自行生成证据文字。
- 要求composer所引短ID对应本例C48中的真passage；映射/文本由冻结corpus重建。不扩大检索，不修改claim、Judge prompt/模型或053 Frozen PriorG。两臂完整输入、预算和解析口径一致。

## 调用次序、恢复与费用

Stage1顺序：96个U planner→96个U composer→冻结所有U结果、passage IDs、reference及其SHA→**才加载GT**→96个T planner→96个T composer→冻结全部B/U/T Judge请求→按`SHA256("081/judge/v1:"+id+arm)`交错发送288个最终Judge。任何科学条件异常或预算安全检查失败，在发送下一阶段前停；不得缩样或用部分结果算主门槛。

普通DNS/断连/超时/429/短时5xx最多原发加2次恢复，退避并可降并发；无成功回答的逻辑请求才可恢复，原未知预留不删。HTTP200内容结构无效不因内容重试。所有请求先落盘、回执绑定SHA、usage计费；Qwen北京保守单价输入¥3/输出¥12每百万token，0731 DeepSeek忙时输入¥3/输出¥9。发送前逐次检查累计+在途预留≤¥20。首阶段完整预计费用和故障缓冲在样本/请求长度可计算后单独冻结；只有完整Stage1安全可行才开始。

## 解析、缺失和评价

- 最终Judge使用053 T-S thinking-high scored完整body；score argmax U0与Frozen PriorG从**同一**合法scores计算。raw原生verdict单列。若HTTP200核心无效，同ID使用事前固定的历史non-thinking U2 fallback（优先052/053，再031），三臂相同；若不存在合法同ID fallback则停止完整主分析，不以临时补标签伪造96。raw/U0/PG各报核心共同有效完整ID与fall-back完整96主口径及具体ID；不因答案好坏重发。
- `verifact_research.evaluation.evaluate`/`paired_compare`，valid-only三分类命题micro，完整同ID、1,000次患者cluster bootstrap。报告correct、PA、MCC、AC1、false-S及非S分母率、逐类P/R/F1、混淆矩阵、患者wins/losses/ties、救回/伤害和GT/作者分层。U−B为可部署信号，T−B为teacher headroom，T−U为GT特权增量；raw/U0/PG分开。
- 记录每例passage数量/字符、相对B增删、重叠、顺序、U/T重叠，token、费用和延迟。历史old-B/new-B exact-body配对只作运行波动，不当新独立病例。必要重复最多从Stage1事前hash取跨患者小集；只在运行波动足以改变gate解释、且费用足够时调用。

## Stage1决定与可选Stage2

**Teacher gate**（全部满足）：T−同期B Frozen PriorG净正确≥+3、rescue覆盖≥3患者、patient wins>losses、false-S增加≤2、收益不全由一患者贡献，且存在若干old-B/new-B均错而T正确的病例。否则停止，不做Stage2/训练。

**Blind gate**：U−B净正确≥+2、rescue≥2患者、patient wins≥losses、false-S增加≤2，且raw或PriorG至少一个核心指标方向稳定。达标只称development初步可部署信号。

若Teacher过、Blind不过，对T干预逐例按beneficial/harmful/no-change/unstable分类；只有稳定beneficial+harmful数量足够、beneficial≥4患者且跨≥2个GT类、并有部署可见的pack/candidate差异特征，才建议下一项utility learning；本轮不训练。若teacher不过或harm抵消，不因066条件oracle修错继续堆packer。

Stage2仅在Teacher或Blind gate过且剩余含缓冲预算可完整覆盖另一96条时才执行；保持所有prompt、模型、formatter与证据约束不变，不做半批。最终报告另给公平适配建议：若上游有可靠变化，后续应患者外等监督预算比较旧PriorG兼容性、旧上游重校准和新上游重校准；081不执行重校准。

事前成果：样本/来源/暴露、C48与原包对齐、U/T共享prompt、证据预算、每阶段请求与费用冻结、gate。运行后：逐次回执、原始分数/预测、pack及逐例转移、统计、成本、自检、交审和中文主报告；不覆盖历史成果。自检不是独立审计。
