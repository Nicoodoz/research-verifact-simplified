# 105：短证据监督与仅标签监督的同样本对照

本地准备阶段，2026-10-28。当前阶段不连接AutoDL、不租卡、不调用收费API、不加载9B训练、不下载权重、不新增磁盘、不提交或推送。下一阶段按本协议接续，不重新选择方案或评价样本。

## 问题与三个配置

检验相同真实训练样本、9B原底座和评价条件下，短证据与核验关系监督能否优于仅三分类标签，重点关注MCC、false-S及NS识别。本轮不是扩大训练或论文确认。

|配置|含义|
|---|---|
|`base_judge`|原始未微调Qwen3.5-9B，使用105共同的104新版输入模板重新评价；103旧预测不替代。|
|`label_only`|104冻结196条，答案为原医生分类JSON。|
|`evidence_brief`|完全相同196条，答案为104冻结的短引用、关系说明及同一医生标签。|

原196条S83/NS62/NA51、40名训练患者。两份文件按原字节复制并锁SHA，同ID、患者、claim、reference、GT、输入模板与顺序，仅答案不同。保留104的机器辅助监督属性，不当成新增医生gold。104派生一致性统计的字符串/整数错误独立更正：从原前三名医生投票重算，196中92条三人一致，unresolved 78中21条；不改训练材料、原GT或回执。更正文件与旧原件并存。

## 模型、训练与loss

复用原`Qwen/Qwen3.5-9B` revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`。两个适配器都从同一原始分片初始化，不接103适配器。完整权重来源、四分片大小/SHA与小文件指纹继承103实机验证记录，下一无卡阶段重新核对实际落盘文件。当前本机只有固定tokenizer/配置与权重索引，不声称已经本地重验18GB完整权重。

BF16、不量化、不CPU卸载；r16、alpha32、LoRA dropout0、bias none、非RSLoRA、视觉冻结。复用103的12种target_modules（见config），预期可训练参数43,278,336。AdamW lr1e-4、betas(0.9,0.999)、eps1e-8、weight_decay0、clip_grad_norm1，microbatch1、梯度累积8、梯度检查点。103没有学习率衰减，105明确采用无warmup恒定调度器，保存其状态。随机种子103027，两臂相同。每轮重复104原始196条顺序，不按长度或标签重排；固定2轮，不看评价挑epoch。

每轮24个完整8条批次加1个4条尾批；每轮25步，总50个optimizer step、392次**提交的**样本消费。尾批每条loss除4，完整批除8。推理只加载固定第2轮完成的适配器。每步写交替两个滚动完整检查点，包含adapter、optimizer、scheduler、Python/NumPy/Torch/CUDA RNG、step/消费数与配置/输入指纹；原子pointer最后提交。中断不写半个累积批次的进度。失败后从最后完整检查点恢复；未提交计算可能重做，费用和恢复事件保留，不把重做冒充新的训练样本。

两臂统一单条loss：`mean CE(final verdict value tokens) + mean CE(other answer tokens)`，其余段为空时为0。仅最终verdict**值**参与分类段；JSON字段名、引号/分隔符、引用、关系及EOS属于其余答案段。prompt/padding目标不计loss。目标在t，由hidden(t−1)预测。没有额外权重、平滑或后处理。

105在重新串行构造与原104字节完全一致的答案时记录verdict值的字符区间，再由固定fast tokenizer的offset映射定位token；禁止通过搜索Supported等字符串定位。跨越值与JSON结构的混合token会拒绝编码。392份真实答案映射已通过本地检查。理由中同名标签不进入分类段。

训练只做一次完整backbone forward，gather预测答案的hidden states，再以16 token为上限分块投影到冻结lm_head；小块FP32 CE非重入checkpoint仅重算head/CE。没有完整序列×词表的FP32 logits，也没有为两段loss重复backbone。小CPU张量已对照完整CE验证loss、梯度、因果位移与mask；实际Unsloth/9B BF16路径、显存与速度须由GPU gate验证，预跑不更新optimizer且不进入正式训练。

## 评价样本与共同推理

只使用103 selection角色20人：池1817条，S1455/NS121/NA241。自然400按GT×作者比例最大余数配额及SHA256固定hash抽取，seed `105/natural400/v1/`；再从剩余ID各取NS50、NA50，seed `105/pressure50/v1/<GT>`，同样按作者比例及hash。自然S321/NS26/NA53（human226/llm174），压力NS50/NA50（human89/llm11）。两个面板无ID重叠；训练与评价无患者重叠。不按103预测对错、长度或104解释合格性选例。没有读取确认40人正文。

全部患者有历史暴露，500中70条曾属于103的选型180；如实称患者隔离开发评价，不称新holdout。GT只用于抽样和离线评价，不传入推理输入。`paper_r1`仅为同ID历史参照，不冒充105 `base_judge`或当前同Judge的verifact_ref。

三臂共同104 `training104.messages`，thinking关闭、greedy、n=1、num_beams1、max_new_tokens384、repetition_penalty1、相同BF16与`parse105.parse`。固定按输入token长度、ID排序，每8行独立prompt左padding推理，末批4行；不是把多条claim装进一个提示。冻结全部分组，相同分组用于三臂。不得裁剪reference。最长完整训练输入含答案12,821 tokens，共同上下文配置13,097覆盖评价及384输出容量。

解析完整JSON的最终verdict；可去外层JSON fence、接受精确单标签，拒绝重复key、不完整/截断输出、从理由抽标签或模型修格式。成功完整批次（含内容无效/截断答案）不因成绩或格式重发。生成后原子保存整批回执；中断未保存批次可恢复重算，另记事件，不替换已保存答案。GPU gate输出不作为正式预测。

## 分析与事前继续标准

自然与压力分开，同ID三臂共同有效集比较，完整冻结N、各臂有效/invalid/缺失及全N的PA、false-S界限单列，不静默填旧答案。MCC/PA/Gwet AC1用项目统一evaluate，差值用paired_compare，1000次患者cluster bootstrap；另报false-S计数/GT non-S分母、预测S假发现率、三类P/R/F1、Macro-F1、救回/误伤与human/LLM分层。区间用于解释，不新增显著性晋级要求。共同有效覆盖不足95%或未收齐固定请求时，工程覆盖不允许判定进入扩大。

`evidence_brief − label_only`自然集满足任一改善：ΔMCC≥0.02，或false-S/non-S下降≥5个百分点；同时PA下降≤2个百分点、false-S率增加≤2个百分点、NS召回下降≤5个百分点。压力false-S不得增加、NS召回下降≤5个百分点。若相对base_judge的MCC与false-S同时变差，不进入扩大。所有结果完整报告；这只是开发继续标准，不是论文确认。不搜索103的180条后处理，不追加epoch或挑更好回答。

## 费用与执行边界

新增计算租金总上限20元，跨无卡/GPU、故障与重启累计；收费API0元，不新增磁盘。使用独立持久账本，禁止用重启或新包重置。18元运行线、2元停机/未知余量。计费从平台实际开机时间开始，不从训练开始。自动守卫绑定当前Linux实例，独立后台运行，worker检查心跳；停止请求后仍须核实平台关机/实际费用，未知区间不能凭发出shutdown释放。

按103真实5448 training tokens/s及直接推理实测估计；短理由平均输出先用104真实目标112.88 tokens作代理，不把384上限当平均。保守预计GPU约2.41小时；仅以历史同卡6.98元/小时算约16.79元，加无卡预留1元约17.79元，另留2元异常余量。实际报价及GPU吞吐下一阶段复核；不同硬件不能照搬速度。现有18GB基础权重与103 venv必须复用，现有空闲磁盘至少6GiB；不下载完整模型或扩容来填缺口。未预测前工程门槛不满足就保存明确缺口，不能借确认患者、换模型、删对照或缩短病历。运行变慢导致完整固定任务不再可负担时停止并报告执行未完成，不看成绩缩规模。

本阶段交付READY_FOR_NOGPU；没有GPU训练、105预测或分类成绩。下一阶段入口为NOGPU_HANDOFF.md，不重新讨论已经固定的科学方案。
