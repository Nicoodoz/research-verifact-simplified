# 项目现状（2026-10-27，103 GPU阶段进行中）

103：qwen3.6-35b-a3b与qwen3.5-9b均已完成512条LoRA训练；qwen3.8-27b按最新用户指令停止，保存40条恢复检查点。两模型必要推理已完成并通过输入/批次核验，35B原生使用已核对的180条API回执，不冒充本地原生对照；不新增API调用，不计算分类效果指标，不升级默认系统。API累计¥27.518576/30，GPU/存储沿原60元及8小时账本；实时状态及完成记录见[执行报告](../outputs/103_lora_selection/gpu_execution_report.md)和[实时进度](../outputs/103_lora_selection/实时进度.md)。102封存不恢复。

[103报告](../outputs/103_lora_selection/report.md) · [GPU接续命令](../tasks/103_lora_selection/GPU_RUNBOOK.md) · [资源要求](../tasks/103_lora_selection/resource_advisory.md) · [102封存更正](../outputs/102_demo_relation/closure.md)。

## 当前研究目标与运行事实

目标是在VeriFact数据集上以相同推理模型、同ID和统一评价形成有实际价值的优势；重点是前处理与Judge raw，不以更强模型或PriorG的收益替代。MCC与false-S相对优先，允许其他指标有合理代价，但须披露误报、三类损失与PA。这里减少false-S指少漏掉真实不一致；不是疾病漏诊率，也不允许靠全判NS/NA制造安全假象。目标不等于已经达成，默认配置未自动升级。

服务更新（2026-10-26）：用户已授权启用https://maas.qianwenaiapi.com/compatible-mode/v1及新Key；主配置.env.aliyun已切换，默认模型deepseek-v4-flash-0731、thinking-high。原配置只留在受忽略的私有备份。此前新端点两次合成调用均HTTP200，无重试；其中thinking-high输入6571/输出288 tokens，估算¥0.022305。连接测试累计保留¥0.159494未对账预留，不因启用新默认清零。旧403记录仍属历史；此次配置切换未新增API调用，不构成临床实验或科学等价证明。

2026-10-26用户更新约定：只说“推送到GitHub”即同时更新research-verifact完整成果归档和research-verifact-simplified关键成果版本；两仓库outputs之外使用同一份允许发布文件快照。没有推送指令仍不自动发布。上次已发布精简版本为34e51aa（2026-10-26）；本次发布状态以两仓库远端main及本地发布回执为准，不以本地文档编辑代替推送成功。发布规则见[AGENTS](../AGENTS.md)。

## 最近结果与可主张范围

099四种Qwen Judge选型已完成；原推荐qwen3.5-35b-a3b、备选qwen3.5-27b保持原结论，不据100改变排名，不自动升级默认。[099报告](../outputs/099_judge_selection/report.md)。

097同V4四臂原生接口对照完成：raw共同158条C48 B/简洁任务/现行B＋G正确116/125/135；固定同body桥接12条raw改变4条。原生任务提供更强raw对照但没有最终系统升级。40例源文核查482条都可定位，405条切开父段；自动依赖和B完整四臂费用门槛未过，B无分类成绩。新增492 HTTP200、0重试、忙时原价¥12.967287/20，自检通过、独立审计未执行，默认不变。[正式报告](../outputs/097_native_judge_source_dependence/report.md)。

096已完成AWQ-Marlin跨Judge与PriorG迁移验证：自然800条Original/V4 raw/R1 raw正确657/617/599；R1重新适配595，旧PriorG直接迁移616且与prior-only同标签。共同798条当前V4＋G正确664、MCC0.5802，R1-adapted594/0.4163。停止本轮适配，默认不变；1143 HTTP200、0重试，AutoDL用户已关机，按token新API0元、GPU租金未知。自检通过，独立审计未执行。 [正式报告](../outputs/096_r1_native_priorg/report.md) · [论文更新](../outputs/096_r1_native_priorg/manuscript_implications.md)。

|研究|实际完成内容|结论与限制|
|---|---|---|
|103微调模型选型|35B与9B各512条训练完成；27B依用户指令停止并保存40条；必要推理已完成|患者角色40/20/40；35B原生复用同ID API参考，微调增量须以本地label_base配对；尚未计算分类收益|
|102动态关系选例|完整500三臂＋24重复输入已构造，0 API；用户明确封存，不补跑|自动构造检查通过不等于关系语义正确；未产生分类指标，付费前停止|
|101 NS/NA定向复核|600自然＋100压力、282触发、24双臂重复；同S集合|plain净-2、review净+0；review−plain净+2；详见正式报告，默认不变|
|097原生Judge/源文门槛|自然160冻结、raw共同158；40例源文离线核查；B无分类调用|C48简洁raw比B raw净+9，但比现行B＋G净−10；B构造/费用门槛未过，默认不变|
|096跨Judge/PriorG迁移|自然800、诊断200；143校准中142有效，R1 G到−6下界|R1 raw与重新适配均未形成综合优势；默认V4＋G不变，AutoDL用户已关机|
|095统一基准/最小差异|B成功覆盖9065/9065、共同core 8997；原作者/B＋G正确7285/7552，MCC0.4983/0.5976|300构造数量通过但语义实施失败，未运行C分类；独立复核范围见报告，默认不变|
|094答案隔离问答|固定C48、生成问题→可见V/隔离Q→同一Judge；自然20条B/V/Q正确19/19/19，机制12条9/8/9|实际操作26/32；Q未超过B，机制false-S由B0至Q1；停止本版，默认不变|
|093固定预算补证|原文折叠F、补证A与同期B；自然90/压力30，core有效88/30；正确B/F/A为76/77/76及17/16/18|自然A净0、false-S+1；压力净+1、false-S−1；原生救回与最终救回不是同一病例，停止本版|
|092任务适配|100人9065条五折OOF，Frozen/Fine正确7204/7530、MCC0.4433/0.5156；同956条B/F4/融合783/793/795|微调有受控增量，NS召回仅8.95%；融合false-S64高于B41，默认不变|
|091综合收束|完整稿、090 raw/score/final诊断；选择性原型可行性|P90 raw净+7缩至final净+2；C材料不足未分类实测|
|090示例压缩|自然176条B/F4/P90/Q90正确145/143/144/144；压力66为34/31/32/32|P90有原生和成本信号，未超过默认，面板分报|
|085正式Judge替换|Valdemardi R1两臂各180；与084缓存比较|raw改善未兑现综合升级；不是Casperhansen精确checkpoint或完整VeriFact复现|
|084固定F4|新180条B/F4正确155/161，false-S6/8|有开发收益及类别代价，不是新患者独立测试|
|078组件消融|384条原作者/当前PriorG正确310/321；StdM/StdV320/319|开发证据；prior-only和完整PriorG在该队列逐例同标签|
|036早期最终评价|reserved40、3573冻结/3571共同有效，U2净+177同时false-S+123|仅确认当时早期边界/Gate/标准校准，不继承为T-S/PriorG/092最终验证|

[095总报告](../outputs/095_anchored_minimal_contrast/report.md) · [095独立复核](../reviews/095_anchored_minimal_contrast/final_review.md) · [094报告](../outputs/094_answer_isolated_verification/report.md) · [094历史区别](../outputs/094_answer_isolated_verification/history_difference.md) · [093报告](../outputs/093_lossless_evidence_budget/report.md) · [093病例分析](../outputs/093_lossless_evidence_budget/case_analysis.md) · [092报告](../outputs/092_task_adapted_verifier/report.md) · [最新完整稿](../outputs/095_anchored_minimal_contrast/manuscript_zh.md) · [研究问题与证据](../outputs/095_anchored_minimal_contrast/evidence_map.md) · [全部任务入口](TASK_INDEX.md)。

## 数据与授权

VeriFact-BHC v1.1.0来自MIMIC-III，共100患者，历史20探索/40开发/40reserved。全体都已有研究暴露；不存在额外未使用20名测试患者。092在用户明确授权下把全部已有标签纳入患者分组CV，9065有效atomic claim，其中human5624/LLM3441，S/NS/NA=7035/693/1337。

095经用户明确授权使用全部100患者，以9065为固定母体；B成功覆盖9065/9065、共同core 8997。构造95自动eligible不等于已部署，语义停止后未运行E/C。092两臂是原OOF，B/PriorG没有按其外层折重新拟合；均不称独立外部测试。

094同样由用户授权使用既有全体材料，实际冻结自然20/机制12，不依赖旧模型对错；问题检查不读GT，GT仅用于登记分层及评价。没有全量新评价或新患者holdout。

093用户允许现有全体患者研究；实际在有完整原生D48材料的1401条中冻结120条同期评价，并非9065条全量分类实测。GT只用于分层及评价，不进选证或推理。

不能再把reserved当未接触holdout；也不能以旧禁用说明否定092实际授权。历史036结果、原GT与分组元数据不改写。后续新研究仍须交办并说明患者隔离、暴露与实际监督范围。

## 环境、模型与部署状态

CPU/API当前为research-verifact-029；032/092本地verifier复用032 GPU环境。092用户在AutoDL RTX4090完成训练，权重/预测/环境记录已转回并核验；云端激活未下载，本地旧缓存另作数值桥接。核心成果不依赖继续保留云实例；本仓库没有执行实例释放，也不声称实例当前仍运行。

085 Valdemardi正式完成；085A/AWS、Casperhansen0.9.2只是保留的准备分支，不是待恢复主线。085的A800/vLLM服务与092的RTX4090编码器训练是不同实验。096已在用户授权的AWQ-Marlin服务完成1143次请求，用户确认关机后全部离线分析；旧AWQ结果仅诊断，无新权重下载。

## 费用、审计与交付

新任务默认API总上限20元；专项不沿用：090曾40元，092曾30元且实际0新增API。GPU租金另账；092价格/完整账单未知。预算与恢复见[API政策](API_POLICY.md)。

095新增API目录价及未知预留¥95.769536/150，7597次尝试，7597个HTTP200；独立执行复核与自检分别留档，非独立医生审评。官方时段价对账不是账户退款或优惠扩额度。

094新增API ¥2.508135/20，157个HTTP200、0重试、无GPU租赁，执行者自检通过、独立审计未执行。

093新增API ¥4.097118/20，153个HTTP200、0重试，无GPU租赁。093与092执行者自检通过，独立审计未执行。更早任务的独立审计仅按[审计索引](../reviews/README.md)中的实际记录引用，不把任务完成、方法通过和审计PASS混为一谈。

历史报告、协议、冻结工件与源文献保留形成时语义。原“092暂停”“085待部署”“尚余reserved”“80元长期预算”等已经过时的现行表述已从主入口移出，原文仍可在[历史快照](history/2026-09-27_before_sync/README.md)查阅。提交/推送按2026-10-14用户最新要求：仅在明确要求时执行。
