# 026 冻结SD的跨患者组迁移：发送前协议

2026-09-19。仅为一次冻结方法迁移验证；所有026调用/效果前先冻结最终gate。任务上限80元，含所有模型、失败、重试及未知预留；不新BGE、不reserved40、不调C/阈值/特征/λ，不新增v2/v3。

## 科研问题与已暴露边界

从024/025的10名development患者迁移到019六名development患者650条原claim/C48。两组患者不交叉；但019材料早已暴露并在025历史分析中使用，不能称从未接触的独立测试集。本轮只验证冻结SD在另一患者组、同阿里云模型条件的新输出上的迁移，不继承019旧SiliconFlow评分。

## 唯一最终gate：先冻结、后发送

训练数据只取025 preparation_001中024_D全部103个λ候选（R76、risk27）。复用learning025.training_threshold：10训练患者内部LOPO概率，取能保留至少80%训练R的最严格阈值；然后在103候选全体拟合最终StandardScaler＋L2 logistic(C=.1,lbfgs,max_iter=2000,tol=1e-8)。不是平均025外层模型，也不是用026选阈值。

特征严格为025的7个S＋5个D，顺序不变；不包含E、患者ID、author、GT或解释。保存训练ID/患者、内部折分、features、mean/scale/coef/intercept/threshold、代码与输入哈希。026推理只读取JSON参数，禁止调用fit；任何026患者不得进入标准化/训练/阈值过程。

## 固定服务与执行

阿里云deepseek-v4-flash-0731、qwen3.8-27b。复用019/024同款scoring prompt、三分类定义、JSON schema；temperature0、enable_thinking=false、max_tokens2048、n1、非stream。完整原claim/reference只见于Judge，不含GT/source/BHC/另一个Judge输出。task-local直连同一阿里云端点，不改系统代理或全项目API政策。

先完成650个DeepSeek scoring；同期保留650个普通structured B作为对照（两臂可交错，均在Qwen阶段前完成）。只有有效DeepSeek S产生U0≠S且U2=S的case才调用Qwen scoring；其余不调用Qwen。候选选择程序只读预测/请求ID，不读GT。预存650份Qwen body只是冻结模板，不代表授权全量发送；执行器以冻结candidate_ids白名单约束。有效非候选直接U0；有效候选SD概率≥唯一threshold则S，否则U0。peer-U2对照只看候选Qwen U2是否S。

沿用024核心字段口径：reason/checks轻微异常记录valid_with_format_anomaly，verdict及S的label_scores唯一合法才可评价；原始response不改。HTTP200一律不重跑，少量core-invalid继续剩余请求。无回答最多3次尝试并保留全部费用预留。系统错误、明确错误模型、滚动100个200里≥10个核心invalid、连续10次通信失败或预算/剩余费用预测超限才停发，收齐在途。

## 价格与保护

发送前核实北京官方DeepSeek0731忙时输入/输出3/9元每百万token，Qwen3.8-27B为3/12；无缓存折扣估算，非账单。来源和预计总费另在registry登记。预估同时包括B＋S，以及保守假设全650条均成候选时的Qwen费用；另留30%余量。每次发送前按请求UTF8字节+2000估输入token上界、输出2048预留，实际+未知+在途≤80。阶段/断点不重置预算；不做额外key探针，最初真实请求直接纳入结果。

## 评价与缺失

U0/U2用同期D评分；SD和peer非候选不需Qwen，候选需Qwen有效。主风险比较使用D有效且候选Q有效的完整方法交集；global-λ参考也用**同一集合**。D-score-only全量曲线另存，不能把不同分母直接相减。B比较用相应有效交集。记录全部排除ID和原因；候选Q无效时部署回退U0只作预登记敏感性，不把失败悄悄计成gate否决。missing-as-error仅PA，不填造三分类标签。

复用002 PA/MCC/AC1/recall/混淆矩阵，all/human/LLM和患者分别报告。R/H/W、rescue retention、新增及总false-S与完整非负global-λ精确断点（直到全S）比较，λ只作事后参考，固定方法仍是2。给出确定性global阶梯、随机混合期望包络的matched-risk/matched-rescue差；不把oracle式参考当新部署λ。

1000次患者cluster bootstrap，仅评价冻结gate，不重训；六患者区间需谨慎。逐一去掉患者检查matched-risk优势，不挑病例。临床风险与PA/MCC代价都披露，不以单一高MCC宣布全面胜出。

## 在结果前固定判断

沿用025主要规模要求：R保留≥80%，新增false-S≤U2的75%，同风险较确定性global多救回≥5 R、较随机混合多≥3 R；至少5/6去掉单患者后的子集仍有正的混合增量，human/LLM对U0净正确均非负。满足为“点估计与患者方向迁移支持”；再加mixed-gain95%区间下限>0为“明确迁移支持”。这些是研发门槛，不是医学安全标准。R或risk为0导致门槛不可评估时如实标不充分，不放宽。

优势消失/明显退化就停止该冻结版本；不重新训练、阈值/C/特征不变。若通过，也只支持进一步冻结正式候选，独立审计后再决定后续；不自动reserved test。
