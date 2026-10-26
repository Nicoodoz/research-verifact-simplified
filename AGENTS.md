# 项目工作约定（2026-09-28，097结项后）

本文件只保留持续有效的约定。先读[项目现状](docs/PROJECT_STATUS.md)、[研究原则](docs/RESEARCH_EXECUTION.md)和[环境](docs/RUN_ENVIRONMENT.md)；查看仓库相关事实前检查实际main HEAD。任务、报告和审计的历史索引见[任务索引](docs/TASK_INDEX.md)，旧说明不覆盖较新的用户授权。

## 研究目标与沟通

研究者为研二，编程和医学基础有限，目标是尽快完成可辩护的毕业论文，并争取合适投稿。导师要求临床文本与患者记录的一致性核验，不强制RAG、MIMIC-IV或某个模型。用中文清楚解释具体问题、结果及限制，不为算法复杂度堆组件。

应用目标是整篇患者临床文档的核验：患者身份和个人EHR已知，系统内部可处理命题，返回问题位置及证据。不能假设获得待核验文档的正确原版。当前评价使用医生标注的原子命题；自由拆分的新单元不能直接继承原GT。

## 当前状态与数据授权

- 097已完成同V4四臂原生接口对照：自然160条，raw共同158条C48 B/原作者式简洁/现行B＋G正确116/125/135；原生raw较B净+9但最终不升级。12条同body桥接raw改变4条。40例源文核查显示482条可定位、405条切开父段；自动依赖构造与完整四臂费用门槛未过，B没有分类成绩。492 HTTP200、¥12.967287/20、0重试；自检通过、无独立审计，默认不变。[正式报告](outputs/097_native_judge_source_dependence/report.md)。
- 096已完成AWQ-Marlin跨Judge与PriorG迁移验证：自然800条Original/V4 raw/R1 raw正确657/617/599；R1重新适配595，旧PriorG直接迁移616且与prior-only同标签。共同798条当前V4＋G正确664、MCC0.5802，R1-adapted594/0.4163。停止本轮适配，默认不变；1143 HTTP200、0重试，AutoDL用户已关机，按token新API0元、GPU租金未知。自检通过，独立审计未执行。 [正式报告](outputs/096_r1_native_priorg/report.md) · [论文更新](outputs/096_r1_native_priorg/manuscript_implications.md)。
- 095已完成：B成功覆盖9065/9065、共同core 8997；同ID原作者/B＋G正确7285/7552、MCC 0.4983/0.5976、false-S 564/347。300构造、117核对后95自动拟触发，但语义核对失败，全局停止C最终Judge/扩量，不能称分类阴性；新增目录价及未知预留¥95.769536/150。默认仍无示例B＋Frozen PriorG；本轮提交后停止，不自动096。 [095报告](outputs/095_anchored_minimal_contrast/report.md) · [独立复核](reviews/095_anchored_minimal_contrast/final_review.md)。
- 094答案隔离式问答完成：冻结自然20/机制12，实际操作16/10；B/V/Q最终正确19/19/19及9/8/9，机制false-S 0/2/1。Q未超过B，唯一Q−V final救回涉及V引用无效，停止本版；费用¥2.508135/20，无重试，默认不变。不自动095。[094报告](outputs/094_answer_isolated_verification/report.md)。
- 093已完成重复原文折叠/固定预算补证首轮：自然共同有效88条B/F/A正确76/77/76，压力30条17/16/18；停止本版，默认不变，费用¥4.097118/20。用户本轮允许现有全体患者材料，实际同期120条；不自动扩大或094。[093报告](outputs/093_lossless_evidence_budget/report.md)。
- 092已完成双臂全量OOF、唯一条件融合、报告、完整中文稿及执行者自检；已提交推送。默认仍为C48→DeepSeek V4 T-S thinking-high→Frozen PriorG，无示例B。G不是双模型Gate。最新论文见[095完整稿](outputs/095_anchored_minimal_contrast/manuscript_zh.md)，092原稿保留。
- 085的Valdemardi AWQ正式实验已经完成；旧085A/AWS与Casperhansen准备分支是历史。不得以旧暂停记录判断正式085未完成，也不得把Valdemardi称为相同Casperhansen checkpoint。092 RTX4090训练与085 vLLM服务分开记录。
- 095获用户明确授权使用全部100患者开展盘点、开发与评价；GT仅用于登记/评价，未进入构造、检索或Judge。095许可不自动授权后续研究，完整开发成绩不称独立测试。
- 100名患者全部已有研究暴露。历史20/40/40划分保留溯源；036已用reserved，092又获明确授权全部标签用于新的患者分组CV。旧“reserved一律不能训练”不能否定092已授权工作；092也不自动授权后续新实验。新任务依明确范围冻结患者隔离，不声称仍有额外未接触20人或新holdout。
- 036只验证早期U2/Gate/标准校准；078是当前系统开发消融，prior-only与完整PriorG在该队列同标签；不能包装为两个独立增益。092微调改善Frozen但NS弱，融合风险未优于默认，不因PA上升自动升级。

## 数据与评价

- data/00_raw保持只读；保留原医生GT、invalid、标注异常和时间冲突，不补造数据、不凭模型解释改标。记录连接键、住院/参考EHR范围和实际输入SHA。
- 医生标签针对完整参考EHR；模型reference仅是实际检索输入，不是医生gold evidence。引用、理由、构造器/核对器输出不是新医生GT或内部推理证明。
- 主指标使用verifact_research.evaluation.evaluate，配对使用paired_compare；允许独立算式/sklearn复核，但不另造标签映射。默认有效atomic claim，固定三分类micro PA/MCC/Gwet AC1，1000次患者cluster bootstrap。不同粒度、作者、有效性、自然/压力面板分开；具体冻结协议优先。
- 主表按“配置｜MCC｜PA｜正确数｜错误支持数”，固定含原作者同ID结果，并报告Macro-F1、三类precision/recall/F1、confusion matrix、false-S/non-S及预测S假发现率。缺失/invalid/fallback单列，不能静默补旧答案。
- label_scores是LLM自报分数，不是真实token probability或已校准概率。区间跨0不等于等效；患者bootstrap不覆盖历史开发选择、重训或新医院泛化。
- 用户可接受084程度的小幅false-S取舍，不把旧+3个百分点门槛当唯一升级标准；NS类别塌缩与总体风险仍完整披露。

## 研究执行与交付

- 新研究必须用户明确交办；讨论、索要提示词、旧TODO不自动启动实验。常规可逆工程和预算内普通通信恢复自行处理，不逐阶段询问。
- 成功回答不因结果不好重发，不默认全量重复；必要同期基线和机制对照不能省。有限重复用于具体稳定性问题，未重复不自动等于方法失败。
- 不同时重选证据、示例、模型和后处理来归因某一组件；按任务冻结配置、样本、费用、停止规则。下一任务、默认系统升级或额外搜索需明确授权。
- 完成报告和自检后保留本地改动；按2026-10-14用户更新，仅在用户明确要求时提交或推送，不得自动commit/push。用户明确要求推送时，可完成该次推送必要的提交。保留用户已有无关改动；自检不冒充独立审计，审计原文不由执行者改写为PASS。
- 历史输入、回执、模型配置、协议、报告和数值保留。现行导航可更新；涉及导航指纹的旧重放使用对应历史快照/隔离checkout，不放宽冻结校验或伪造旧manifest。

## API调用费用与确认规则

默认一次新任务全部新增收费API累计硬上限人民币20元，用户专项上限优先；按未优惠原价计，包括预检、所有阶段/模型/账号、重试、未知及在途预留。不得拆任务、换key、跨供应商或暂停恢复重置额度，也不结转历史余额。超有效额度或无法合理估算时报告明确缺口。

Judge直接阿里云DeepSeek，任务冻结实际模型ID；可选Qwen同路。Embedding/reranker优先既有缓存，默认硅基流动Pro BGE；092已授权的本地补齐分支不代表全局API等价。不得以旧“全池耗尽后才切阿里云”阻止当前Judge路由。停用account_1不重启；无意义余额/密钥探针不做。

只对未成功回答请求有限重试、退避及降并发。HTTP0需区分未送达和计费未知，未知预留不能无据释放；HTTP200核心无效按协议处理，不按内容重试。持续权限/模型/数据/预算问题才报告阻塞。详情见[API政策](docs/API_POLICY.md)。

AutoDL实例由用户管理；不自动购买、部署或下载权重，不存SSH密码/token。GPU小时租赁和API分账，不把20元API上限套成租金授权。

## 开发环境与隐私

- Windows用pwsh；保留既有编码和换行，新文件UTF-8无BOM。搜索优先rg。不得擅改.gitignore。
- CPU/API主环境research-verifact-029，用scripts/run_research.ps1激活；environment.yml声明现行关键依赖。旧research-verifact配置在environment.legacy-analysis.yml，不能混称现行主环境。
- 032/092本地GPU复用.local_models/032/venv加research激活，关键依赖见environment.local-verifier.yml；021 BGE见environment.local-bge.yml；092云端Python3.12/RTX4090见environment.autodl-verifier.yml与原环境快照。不擅自升级、重装或切换旧实验环境。
- 不提交临床原文、私有回执、密钥、权重或缓存。不能用git未跟踪判断可删除，先区分新成果与可重建文件。

## 文档维护

现行状态在PROJECT_STATUS，现行规则在本文件/RESEARCH_EXECUTION/API_POLICY，环境在RUN_ENVIRONMENT；不要将几十轮相互覆盖的“最新”段落继续堆到顶部。新增状态同时检查入口与配置。所有旧阶段细节可从[历史导航快照](docs/history/2026-09-27_before_sync/README.md)及正式报告查询，不删改研究历史。
