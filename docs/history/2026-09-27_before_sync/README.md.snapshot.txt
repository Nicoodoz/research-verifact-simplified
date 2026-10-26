# Research-VeriFact

**092完成（2026-09-27）：** 用户AutoDL训练后，本地完成100患者9065条双臂OOF与唯一融合。原作者/Frozen/Fine正确7331/7204/7530，MCC0.4959/0.4433/0.5156；Fine较Frozen净+326、false-S764→745，但NS召回仅8.95%，不能全面超越原作者。共同956条B/F4/Fine/偏置对照/融合正确783/793/770/786/795，融合较B净+12但false-S41→64、MCC未提高；较偏置对照净+9且false-S−15，保留有限增量、不升级默认。完整中文稿和类/患者/成本分析已更新；0新收费API，云GPU租金未知。执行者自检PASS，独立审计未执行。092明确授权全部100人标签用于新患者分组CV，不改036历史、不称新holdout；旧本地暂停工件另存，不自动093。 [报告](outputs/092_task_adapted_verifier/report.md) · [完整稿](outputs/092_task_adapted_verifier/manuscript_zh.md)。

**092用户暂停（2026-09-27）：** 任务适配文本核验实验已按用户指令停止，包括训练及父级流水线。9065条/100人C48和47219窗口编码完成；Frozen fold0完成，Fine-tuned fold0保存至第5轮1024/5685，其余折未启动。全量OOF和方法比较未完成，不判定成败。私有检查点/缓存保留，0新收费API；默认与历史成果不变。本轮曾获明确授权全部100人标签用于新患者分组CV，不改写036历史。只有用户明确恢复才继续；本次按要求交接并推送。 [暂停报告](outputs/092_task_adapted_verifier/report.md)。

**091最新（2026-09-27）：** 091综合研究完成：新完整中文稿按证据/原生判定/决策边界组织；090自然167共同core的F4/P90 raw120/127、PriorG135/137，净优势7→2分解为7−4−1+2−2，未见一致类对排序改善；压力65最终净0，完整66净+1涉及fallback。C数值—单位原型盲盘点17条/8人、缺口4条/3人，未进入分类实测。0新API、¥0/20，未拟合或改默认；独立算式及执行者自检PASS，独立审计未执行。085已正式完成，旧暂停按历史理解；036仅用汇总、不用reserved开发，不改.gitignore、不自动092。 [报告](outputs/091_integrated_evidence_decision_study/report.md) · [完整稿](outputs/091_integrated_evidence_decision_study/manuscript_zh.md)。

**085 Valdemardi正式完成（2026-09-27）：** 180条/21患者的R1-B/F4各180个首次HTTP200，原Stage B三条复用、357条新增。177条raw共同有效R1-F4较V4-F4净+13，但false-S增加8/30；全180条R1-F4＋Frozen PriorG较现行V4-B＋G仅净+1、MCC下降、false-S增加5/30。默认不变；0重试，自检1853＋61项PASS，实例租金未知。旧085A/AutoDL身份锁不回写、reserved未用。[正式报告](outputs/085_r1_70b_valdemardi/report_formal.md)。

**085 Valdemardi A/B最新（2026-09-27）：** 用户另行恢复085；本机loopback实际服务为Valdemardi AWQ、20K上下文。冻结360条B/F4仅换Judge model；虚构A和三条冻结B均首次HTTP200，实际输入token与新模板一致。剩余B179/F4 178未调用，串行预测2.85小时、50%余量4.27小时；本实例时价未知。旧Casperhansen/085A/AWS不回写，0评价GT、0正式批量，默认不变；需另行授权formal。 [报告](outputs/085_r1_70b_valdemardi/report.md) · [预测](outputs/085_r1_70b_valdemardi/forecast.json)。

**090最新（2026-09-27）：** 090固定示例构造修复与同期比较完成：P两长槽真实构造，第2工程版只分离不相容来源替代项并补回具体遗漏；自然176条B/F4/P90/Q90＋PriorG正确145/143/144/144，压力66条正确34/31/32/32，两面板分报。原价及未知预留¥32.964970/40，构造/测试/核对¥0.094507/4。自检PASS、独立审计未执行。默认不变、不用reserved、不改.gitignore；新临床原文/回执仅私有忽略目录，公开ID/哈希/指标。今晚085/AutoDL/AWS/R1暂停，Casperhansen0.9.2与Valdemardi0.10.1.1差异只备忘、不改身份锁；不自动091。 [报告](outputs/090_demo_constructor_repair_validation/report.md) · [085备忘](outputs/090_demo_constructor_repair_validation/085_resume_memo.md)。

**085 AutoDL恢复（2026-09-26）：** 用户恢复085并改走手工管理AutoDL/direct vLLM；旧085A/AWS文件和暂停历史不改。精确AWQ仓库及resolved revision已锁定，084的180条/21患者与360个B/F4输入复用，V4不重调。离线adapter/脚本/manifest/账本/预检及评价就绪，自检2308项、11项测试PASS；0推理/0新API费，实际GPU与端点未验证，租金未知。等待用户建立tunnel、提供实际manifest与小时单价；A/B后先预测费用，正式大批量须另行明确授权。默认不变、不用reserved、不改.gitignore、不自动其他任务；正式085完成后提交推送。 [操作说明](tasks/085_r1_70b_autodl/AUTODL_HANDOFF.md) · [离线报告](outputs/085_r1_70b_autodl/report_offline.md)。

**089最新（2026-09-26）：** 089固定示例压缩实测完成：P长槽排序接口失败保留全文，P4=F4共享同体；Q仅NS示例缩短。自然110条F/P/Q正确87/87/90，MCC 0.4939/0.4939/0.5388；压力44条正确26/26/22，两面板分报。349次尝试、原价¥13.168865/20。P覆盖机制未成功测试，不把同体零差当等效；不升级默认、不自动090。自检PASS、独立审计未执行；085A/R1/AWS继续暂停。 [报告](outputs/089_source_audited_demo_compression/report.md) · [交审](outputs/089_source_audited_demo_compression/audit_handoff.md)。

**088最新（2026-09-26）：** 固定示例原文抽取原型完成；两条短S保留，NS/NA长例均被固定Qwen构造器标记保留全文，最终P4=Q4=F4逐字相同、0%压缩。按事前第6节停止无信息量主重复，分类质量未评价、P特有机制未测试，不能写成等效或压缩原则上不可行。2次构造HTTP200、原价¥0.0034556/20，源核对/Q构造/主Judge均0次；自检136项及8项合成测试PASS，独立审计未执行。默认B/Frozen PriorG不变，087/086不回写，085A/R1/AWS暂停，不用reserved、不改.gitignore、不自动089；按用户授权提交推送。[088报告](outputs/088_evidence_preserving_demonstration_compression/report.md) · [决策](outputs/088_evidence_preserving_demonstration_compression/decision.json)。

**087最新（2026-09-26）：** F4证据信息干预完成，22名development患者110条同期B/F4/CL4/X4＋Frozen PriorG正确95/96/92/93、MCC0.6588/0.6817/0.5920/0.6264、错误支持5/5/7/5。共同核心有效105条raw正确81/84/82/80，F4对X4有有限单轮对应关系敏感性信号，不证明具体推理技能；CL4输入少62.47%、费用少38.22%，未证明等效或可替代。440次HTTP200、原价¥14.419416/20，自检4227 PASS、独立审计未执行。086补正为有效评分1救回/3伤害＋fallback相关1救回，原主结果不变。默认B＋Frozen PriorG不变，085A/R1/AWS继续暂停；不使用reserved、不改.gitignore，不自动088，完成后按用户授权提交推送。[087报告](outputs/087_f4_evidence_intervention/report.md) · [086补正](outputs/087_f4_evidence_intervention/086_correction.md)。

**086最新（2026-09-26）：** 086固定四例全局效用选择完成：D/V/E为6/12/22患者，V36条五组实测选中N1，E110条同期F4/N1/R1＋Frozen PriorG正确93/92/92、MCC0.5944/0.5784/0.5944、错误支持4/4/3；原价¥21.150990/30，522次尝试，自检1629 PASS，独立审计未执行。085A已原位暂停，R1/AWS未部署或调用；默认B＋Frozen PriorG不变，084历史门槛不回写。用户接受小幅错误支持取舍但本轮三类风险仍单列。不用reserved、不改.gitignore，不自动下一任务。[报告](outputs/086_global_demonstration_selection/report.md)

**085A最新（2026-09-26）：** 已为JumpStart R1-Distill-Llama-70B替换实验冻结084的180条/21患者、360条B/F4中立输入；官方tokenizer审计B 2592–3918、F4 8368–9694 chat tokens，8K容器无法容纳F4。AWS只读诊断、显式推理gate、延后预检/解析/四臂评价框架齐备，2194项自检PASS。未部署、0推理/¥0、未用reserved或评价GT调方法；默认系统不变。等待用户手动部署，正式085未启动；本具体任务不commit/push。[报告](outputs/085_r1_70b_model_swap/report_predeploy.md)

**推送约定更新（2026-09-26）：** 用户要求今后每完成一个完整任务后提交并推送GitHub；084结项时的“不commit/push”保留为执行时快照，本次在用户后续指示下另行推送。

**084最新（2026-09-26）：** 083冻结OOF零API诊断确认NS塌缩在训练侧已可见。084全仓库C48扩覆盖新增180条/21患者，固定B/F4＋Frozen PriorG正确155/161，MCC0.5881/0.6433，错误支持6/30→8/30。净+6但非S错误支持率+6.67百分点，超过事前3点容忍，患者区间跨0；默认B＋G不变，F4仅作有代价的开发候选。071选例训练患者池与新队列121条/14人重叠，池外59条/7人，全部仍是暴露development。360次HTTP200、原价¥12.166821/20、0重试；自检6043 PASS、独立审计未执行。不用reserved、不改.gitignore、不commit/push、不自动085。[084报告](outputs/084_f4_coverage_validation/report.md)

**083最新（2026-09-26）：** 原生F4理由459条/14患者同监督学习、旧352＋新180条/22患者外评价完成。F4＋Frozen PriorG为447正确/MCC0.5703/错误支持21，分数＋raw的N为451/0.5250/47，细结构R为443/0.4686/51。R较N/G/T均少判对；错配理由负对照与R同为443，新增180相对F4＋G净−7、错误支持+15。原生reason/checks覆盖1015/1015，新增Qwen提取1015次HTTP200、原价¥0.620007/20；自检22065 PASS、独立审计未执行。默认B＋G不变，停止当前理由抽取纠错版本；不用reserved、不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送083，不自动084。[083报告](outputs/083_native_rationale_information/report.md)

**082最新（2026-09-26）：** 完成14患者302条配对锚点的代表性／等规模边界覆盖比较，旧352＋新180共532条/22患者外评价。B＋Frozen PriorG、F4＋Frozen PriorG、F4独立校准、F4共享＋配置修正正确438/447/436/453，MCC 0.5481/0.5703/0.5457/0.5622，错误支持18/21/18/33。配置修正训练风险门槛失败，在新180相对F4＋G净正确0、错误支持+7；边界覆盖独立校准只回到G。未优惠原价¥35.281902/50，1070次新HTTP200；24条同体重复、自检3750 PASS，独立审计未执行。默认B＋G不变，停止本版评分适配；不用reserved、不改.gitignore、研究结项时未自动提交推送；用户后续单独授权推送082，不自动083。[082报告](outputs/082_anchor_configuration_adaptation/report.md)

**081最新（2026-09-25）：** 24名development患者96条GT盲选证U、GT教师T与同期原包B比较，Frozen PriorG正确71/73/74，raw为67/70/67；首轮Teacher/Blind gate均PASS，但配对区间跨0。48条患者哈希重复中，U−B净0→−3、T−B净+1→−4；T−U首轮净+1全部来自U/T完全同包的Judge波动。未证明稳定选包收益或GT特权增量，停止本版final-pack selector/utility learning，默认B不变。816个HTTP200、1个HTTP0保守预留，累计估算¥17.467488/20；Stage 2完整预算不足。执行者自检1299 PASS，独立审计未执行；无reserved、不自动082；研究结项时未自动提交，随后用户另行授权推送。 [081报告](outputs/081_gt_blind_evidence_selection/report.md)

**080最新（2026-09-24）：** 080最终分类目标适配完成，0 API、0元。112条/14人校准留一验证为F4选WMCC1（直接优化加权MCC、只调S）；352条/22人上正确291，MCC0.5576，较旧F4的298/0.5771净−7，错误支持12→10。预设WNLL1/2候选均304正确、MCC约0.5876/0.5878，但错误支持17、NS召回24%，且未被校准选择。有提高PA/MCC的风险取舍候选，未实现可靠的跨患者适配；不改默认、不追加本轮搜索、不自动081。自检PASS，独立审计未执行。 [080报告](outputs/080_final_decision_adaptation/report.md)

**079最新（2026-09-24）：** 079固定F4对称PriorG适配完成：114条/14人校准，复用19条F4、新增95条，共同有效112条分别拟合B/F4两个G；352条/22人评价，F4新/旧PriorG正确295/298，MCC 0.5689/0.5771，新F4较旧F4净-3、错误支持-1；较对称B新PriorG净+1。费用估算¥3.988890/20，两个拟合参数先冻结再评价，无搜索。已暴露development；自检PASS，独立审计未执行。 新F4适配净−3、错误支持−1，无整体升级；停止本次单参数适配，不再搜索，保留F4既有开发信号与原默认，不自动080。 [079报告](outputs/079_f4_priorg_adaptation/report.md)

**078 F4补充更新（2026-09-24）：** 078固定F4已补齐384条：复用128条、新补256条，新增256次请求，核心有效252条；补跑估算¥10.484094，078累计¥31.527954/35。排除示例患者后的352条，F4相对无示例raw/U2/PriorG净正确+5/+9/+4；F4＋PriorG MCC 0.5771，无示例0.5672。完整384含2条示例本身、32条示例同患者病例，仅描述性展示；352仍有示例候选池重叠，原128保持全候选池隔离。未重新拟合PriorG，未改变默认系统。 [补充报告](outputs/078_component_ablation/f4_extension_001/report.md)

## 现行摘要（2026-09-24，078结项后）

- **078组件消融：** 078组件消融完成：主384条/24患者，原VeriFact与当前PriorG正确310/321，MCC 0.4840/0.5887；患者外StdM/StdV正确320/319。192条证据桥接与128条F4次级比较完成，F4＋PriorG较无示例净+2、false-S +2。新增752条HTTP200，费用及未知预留¥21.043860/30；Gate采用患者外参数。已暴露development消融，不是新最终测试；自检PASS，独立审计未执行，不自动079、不提交推送。[078报告](outputs/078_component_ablation/report.md)。
- **077判别信息：** 077零API判别检查完成：B/F4去重共同有效262条、16患者；最早/最晚平均类别对AUC差+0.0040/−0.0044，无全面排序改善。0–20%错误支持率预算下经验混合包络平均PA差+3.75/+4.06个百分点，患者区间跨0；两口径逐患者及任务块留出仍正，但075/80606影响大，LLM方向不稳。仅保留F4低风险工作点的有限验证价值，不升级默认、不再改示例、不重启通用自适应。0元、0拟合，自检PASS，独立审计未执行，不自动078、不提交推送。[077报告](outputs/077_static_example_discrimination/report.md)。
- **076统一整理：** 076零API整理完成：原生重建071–075共1164条逻辑输出，实际264条不同命题、16名评价患者。F4按同ID最早/最晚一对去重，final净+3/+1、false-S均+6；raw共同有效262条净+5/+4，区间均跨0。075存在raw与PriorG方向反转，但动态/批注也有raw损伤，不能归咎单一环节。默认B和Frozen PriorG不变，停止当前示例微调、暂停final pack方法开发，优先论文收束。0元、0拟合，自检PASS；独立审计未执行，不自动077、不提交推送。[076报告](outputs/076_existing_results_synthesis/report.md)。
- **075静态批注：** 075固定四例批注已完成：36条探索B/F4/R4最终正确27/23/24，raw共同有效36条正确24/26/24；未通过探索条件，未执行60条确认，停止本版本。默认B不变，累计估算¥4.100976/20，108个HTTP200、108核心有效；自检PASS，独立审计未执行，不自动076、不提交推送。[075报告](outputs/075_annotated_static_examples/report.md)。
- **074混合教学示例：** 074固定锚点＋动态补例已完成：36条新命题探索B/F4/F6/H6最终正确27/27/25/26；混合方案未进入确认，停止本版本。默认B不变，累计估算¥6.667080/20，144个HTTP200、144核心有效；未重复成功同体、未用reserved、未改.gitignore，自检PASS，独立审计未执行，不自动075、不提交推送。[074报告](outputs/074_anchor_dynamic_examples/report.md)。
- **073临床教学示例匹配：** 073已完成：新命题36条探索B/F4/D4/L4/M4正确31/33/30/31/31；修正词汇和缓存BGE语义匹配未超过静态F4，按事前规则停止动态版本。F4探索净+2含1条输出截断后的历史U2回退，不能全部归功于示例。另10人60条开发确认B/F4正确49/49，MCC 0.6698/0.6419，净+0，false-S变化+2；未达确认门槛，默认仍B。累计估算¥11.857017/20，295/295 HTTP200（293核心有效），成功同体不重复；自检PASS，独立审计未执行，不自动074、不提交推送。[073报告](outputs/073_clinical_example_matching/report.md)。
- **基准：** C48冻结证据 → DeepSeek T-S thinking-high评分 → Frozen PriorG；默认仍用无示例B。后处理暂冻，final pack暂停方法开发。
- **072静态/动态教学示例：** 6人36条探索后选D4，另10人60条开发确认中PriorG正确B/F4/D4=44/47/48。D4−B净+4、false-S不变，但D4−F4仅净+1、false-S+1，未达事前升级门槛；18条D4/F4完全同体的调用波动贡献全部+1，真正换例子的42条净0。F4−B净+3也未达静态门槛。证据不足以升级，保留B；324/324 HTTP200，费用估算¥12.971532/30，自检864 PASS，不自动073。[072报告](outputs/072_adaptive_judge_examples/report.md)。
- **071首轮：** 16名development患者96条，B无示例/E正确示例/C错配标签的最终正确数78/83/79，MCC 0.5309/0.6250/0.5208，false-S 3/3/5。E−B为5救回、0伤害；raw共同有效93条正确70/73/71。NS仍0/5，5个final救回中3个仍依赖PriorG改判；重复性和具体证据关系学习未验证。用户决定首轮结项，不自动续跑或启动072。
- **执行原则已更新：** 不默认全量重复成功实验；费用优先用于有依据的策略比较或增加覆盖。普通通信故障在预算内自动有限重试、退避、必要时降并发后恢复；不因少数瞬时HTTP0逐次请求批准。成功回答不重发，原未知预留与重试费用均入账。详见[研究执行原则](docs/RESEARCH_EXECUTION.md)与[API政策](docs/API_POLICY.md)。
- **现行默认预算20元/新任务**，沿用071用户更新；072获单任务30元专项上限，其他历史预算不追溯改写。
- **数据与证据等级：** development40人均已使用，reserved40在036已完成最终评价且有后续事后分析，不再用于开发或称未接触测试集。066–078的oracle/诊断与development结果不冒充最终确认；072执行者自检864 PASS，独立审计未执行。
- 结果入口：[072报告](outputs/072_adaptive_judge_examples/report.md) · [071报告](outputs/071_judge_icl_feasibility/report.md) · [053基准](outputs/053_thinking_prior_validation/report.md) · [067更正](outputs/069_final_pack_controlled_repair/067_correction.md)。

## 历史阶段记录

以下阶段结论、预算、停止及授权按形成时理解；不自动授权后续任务。现行策略以本页摘要、研究执行原则和API政策为准，冻结报告与协议不追溯改写。

**071阶段记录：** 4例其他患者三医生一致教学示例、16人96条B/E/C三臂首轮已完成。Frozen PriorG正确数B/E/C为78/83/79，E−B净+5且false-S不变，E−C净+4；raw共同有效93条为70/73/71。首轮效果gate PASS，但预设192次同体重复的安全费用界¥21.526474超过本任务20元上限，预算gate FAIL；用户决定不重复、按首轮结项，稳定性和证据关系学习均未证实。原6条通信未知回执及预留保留，295次071尝试、总费用及未知预留¥12.063351/20元，自检509 PASS；不自动072、不commit/push。[071报告](outputs/071_judge_icl_feasibility/report.md) · [逐例审阅](outputs/071_judge_icl_feasibility/stage1_case_review.md)。

**070阶段记录：** 固定C48→final reference及Frozen PriorG完成零API推理诊断。237条共同有效病例上，DeepSeek non-thinking / thinking raw / Qwen U0相对G分别救回/伤害9/28、1/19、11/23；066 oracle修复14条的成功候选均无同体复验，部分答对的解释不被final reference直接支持。NS/NA边界有重复线索但镜像伤害显著，暂停推理方法开发，先澄清标签契约。自检68 PASS，独立审计未执行；不自动071、不commit/push。 [070报告](outputs/070_fixed_evidence_reasoning_diagnosis/report.md) · [逐例台账](outputs/070_fixed_evidence_reasoning_diagnosis/case_ledger.md)。

**069阶段记录：** 066 C48内oracle修对的10条错误完成原包／oracle重复与只增、只删、组合受控对照。严格要求原包两次均错及操作两次均对后，稳定救回分别为只增2、只删1、组合1，均未达≥3条且≥3患者的事前门槛；GT盲第二步未启动。64/64 HTTP200，估算¥1.828542/8元，自检574 PASS，独立审计未执行；不自动070、不commit/push。 [069报告](outputs/069_final_pack_controlled_repair/report.md) · [067更正](outputs/069_final_pack_controlled_repair/067_correction.md)。

**068阶段记录：** final pack效用诊断完成。发现067 v1原包ID全空，所谓保守增补实际为约12段→1–2段替换；067较早v2冻结与较晚主报告互相冲突。v2修正分支raw正确177→181，PriorG后198→200但两条final救回同输入重复均未重现；不训练selector，先独立审计067来源口径。068新增164/164 HTTP200，估算¥3.785280/10元，自检PASS，独立审计未执行；无reserved、不自动069、不commit/push。 [068报告](outputs/068_final_pack_utility_diagnosis/report.md) · [当前状态](outputs/068_final_pack_utility_diagnosis/CURRENT_STATUS.md)。

**041阶段记录：** evidence-gated explanation synchronization已完成执行与自检。C48-only为83/342个U2翻转生成严格证据解释，R覆盖66/219=30.14%，H/W false-justification 17/123=13.82%；Expanded为153/342，R覆盖121/219=55.25%，但H/W false-justification升至32/123=26.02%。0 API，不选winner。 [041报告](outputs/041_evidence_gated_explanation_sync/report.md)。

**040阶段记录：** 039结果落在预设规则未显式覆盖的混合区域：有效R中A66、B55、C94、D1；A+B=56.02%，但A<50%且B不超过A。零API，记录为mixed mechanism，041同时报告C48-only/Expanded选择性工作点。 [040报告](outputs/040_route_decision/report.md)。

**039阶段记录：** 完整eligible EHR高召回归因已完成执行与自检。219条R中A66、B55、C94、D1、U3；121/219=55.25%可建立自动化完整支持，其中55条需C48外证据。H/W仍有32/123通过A+B，因此不能把自动证据审计直接当安全gate。924个HTTP200，约17.291343元；独立审计待进行。 [039报告](outputs/039_full_ehr_attribution/report.md)。

**038阶段记录：** 证据—标签—解释一致性审计已完成执行与自检，独立审计待进行。U2最终Supported 2647条中346条（13.07%）继承原scoring non-S解释，Qwen解释审计346/346判contradictory；219条GT=S救回中，Qwen有效214条里68条判S、51条strict trace-supported。该自动审计不是医生gold，结论是label增益不能自动外推为证据/解释增益。1270个HTTP200，约12.052元；不改036预测、不重新调方法、不自动039。 [038报告](outputs/038_evidence_explanation_audit/report.md) · [038交审](outputs/038_evidence_explanation_audit/audit_handoff.md)。

**037阶段记录：** 用户另行授权的development探索已执行并自检通过，尚未独立审计。保持Std_V的Supported集合，V/M固定切换在3675条患者外结果上NS召回8.08%→39.06%，PA83.84%→84.38%，false-S237不变，但NA召回71.75%→56.91%。Logistic逐条等同固定切换，未有额外增量。0 API，未重新读取/评价reserved，不自动提交、推送或038。 [037报告](outputs/037_ns_na_decision/report.md) · [037交审](outputs/037_ns_na_decision/audit_handoff.md)。

**036阶段记录：** 036已执行reserved40全部3573条最终验证，2条核心无效，共同有效主分析3571条。U2较U0净正确+177、false-S +123；A Gate较U2净正确-22、false-S -63。标准M/V总体PA/MCC更高，但类别代价明显，λ2不是最强后处理；论文应定位边界/置信度/风险的实证研究。另有事前冻结4人444条重复。累计费用及未知预留105.576735/150元；执行者自检PASS，独立审计待进行。reserved已用于最终评价，不再用于开发；不自动037。按本轮用户授权，完成后直接推送，不等待独立审计。 [中文总报告](outputs/036_final_validation/report.md) · [论文写作交接](outputs/036_final_validation/paper_handoff.md)。034/035中的“不启动reserved40”为历史任务边界，036由本轮用户另行授权，长期80元API政策不变。

**034–035阶段记录（2026-09-20）：** 快速独立审计PASS，可冻结／结项。034完成3675条同ID系统比较；035固定λ2加温度保持标签、降低NLL但整体Brier略升，不能包装为全面概率改善。035原生库启动故障已通过正确conda激活解决，无需重装；17个联合NLL拟合以SLSQP复核一致。当前API-BGE/Judge/Gate主环境统一research-verifact-029，经scripts/run_research.ps1启动；本次不启动reserved40。 [034报告](outputs/034_same_data_comparison/report.md) · [035报告](outputs/035_lambda_boundary_calibration/report.md) · [034审计](reviews/034_same_data_comparison.md) · [035审计](reviews/035_lambda_boundary_calibration.md) · [环境入口](docs/RUN_ENVIRONMENT.md)。

**033阶段记录（2026-09-20）：** Gate训练subset研究已快速独立审计PASS，可冻结／结项。复用030全部4356模型/1452集合，23个定向集合仅新增36个最终拟合；含必要OOF基线共178个新最终模型。A3核查较全训练多4正确但多1 false-S，同风险−1.20R；D5同风险仅+0.40R且rescue保留76.1%。未找到稳定更优subset，建议A保留全development40人训练覆盖，A3仅作小幅工作点收益备选。0 API、未用reserved40、不自动后续；本轮用户授权审计通过后提交推送。旧033 reserved准备已撤回改名归档，本033不沿用其任务。 [主报告](outputs/033_gate_training_subset/report.md) · [推荐名单](outputs/033_gate_training_subset/recommendation_001/training_patients.csv) · [独立审计](reviews/033_gate_training_subset.md)。

**032阶段记录（2026-09-20）：** 证据关系增强三分类纠错已快速独立审计**PASS，可冻结／结项**。28名/2527条训练，12名/1148条已暴露确认；NLI配对54236组、135套保存模型。双粒度注意力主方案954/1148，PA 83.10%、MCC 0.4960、错误Supported 77；λ=2参照947/1148，PA 82.49%、MCC 0.5210、错误Supported 57。未实现PA/MCC共同提高，不因辅助结果改选主方案。0新收费API，未使用reserved40，未修改主环境或029环境，不自动033；本轮用户授权通过后提交推送。[主报告](outputs/032_evidence_relation_correction/report.md) · [当前状态](outputs/032_evidence_relation_correction/CURRENT_STATUS.md) · [独立审计](reviews/032_evidence_relation_correction.md)。

**031阶段记录（2026-09-20）：** 固定信息组合的训练扩充/患者隔离确认已快速独立审计PASS，可冻结／结项。原16人扩至28人，另12人1148条完整确认；扩充后A/B正确数不变，C/D各+1。主要同风险混合差C−A为−3.50R、D−B为−5.14R，未确认新增核查信息的实质增量，停止当前版本；A仅保留简单参照。费用及未知预留37.70924338/80元，不使用reserved40、不自动032；本轮用户授权审计通过后提交推送。031由用户另行授权，不回写030边界；长期API政策和主环境未改。 [主报告](outputs/031_training_expansion_confirmation/report.md) · [独立审计](reviews/031_training_expansion_confirmation.md) · [离线复查](outputs/031_training_expansion_confirmation/audit_handoff.md)。

**030阶段记录（2026-09-20）：** 固定Gate训练规模/组成分析已快速独立审计PASS，可冻结／结项。141个不同评价轮次，4356最终模型；11人训练时D对A/B合并平均同风险+5.11/+3.83R，但025子组仍多次反向、D更敏感。14人仅复现029锚点，不能据零波动证明组成稳健；现有数据不足以确定稳定最低人数或来源配比。0 API，不自动扩大训练材料、031或reserved40。 [主报告](outputs/030_gate_training_stability/report.md) · [独立审计](reviews/030_gate_training_stability.md)。

**029阶段记录（2026-09-20）：** 离线36组实验已快速独立审计PASS，可冻结／结项。联合repeat+trace的Logistic在患者OOF相对A/B同风险混合包络多11/9R，保留该开发信号；反向迁移保留率71.1%，优势未稳定复现，XGBoost无可靠补救。不选winner、不继续特征/分类器搜索、不自动030或reserved40；0 API、0费用，独立029环境，未改历史结果。 [主报告](outputs/029_semantic_information_gate/report.md) · [独立审计](reviews/029_semantic_information_gate.md)。

**028阶段记录（2026-09-19）：** 可追溯主张—证据核查已快速独立审计PASS，可冻结／结项。155个development候选，两臂各155次核心有效；trace仅保留44/110真S救回，相对SD完整队列净−40，相对repeat+9但区间跨0。未稳定超过完整global-λ参考，停止当前语义核查版本。费用估算3.798027/80元，不改λ/C48/历史结果，不自动029或reserved40。 [主报告](outputs/028_traceable_claim_evidence_verification/report.md) · [独立审计](reviews/028_traceable_claim_evidence_verification.md)。

**027阶段记录（2026-09-19）：** 双Judge迁移瓶颈离线诊断已快速独立审计PASS，可冻结／结项。026排序仍有信息，但≥80% rescue区对完整global混合包络最多+2.368R，不能仅换阈值恢复门槛；22/52候选存在精确输入冲突。组成与概率尺度变化并存，现有证据不足以支持仅改工作点／融合器继续救Gate。0 API、0新增拟合、不改λ、不用reserved40，完成后停止。 [主报告](outputs/027_dual_judge_transfer_diagnosis/report.md) · [独立审计](reviews/027_dual_judge_transfer_diagnosis.md)。

**026阶段记录（2026-09-19）：** 冻结SD跨患者组迁移已快速独立审计PASS，可冻结／结项。6人650条，D评分/B各650，仅52个候选调用Qwen；1352个核心有效，费用估算16.782714/80元。SD保留29/34救回、新增false-S18→12，但相对完整global随机混合包络仅+2.11R，留一患者4/6为正，未达事前门槛；停止当前版本，不调参、不自动reserved40。 [主报告](outputs/026_frozen_sd_patient_transfer/report.md) · [独立审计](reviews/026_frozen_sd_patient_transfer.md)。

**025阶段记录（2026-09-19）：** 离线风险可分性分析完成，快速独立审计PASS，可冻结／结项。E未证明超出score/global λ的稳定增量，停止当前E路线；024D第二Judge信号有正向OOF增量，仅保留有限开发线索，历史D不可评估、Qwen未复现。固定λ=2、0新增API、未用reserved40，不自动后续。 [主报告](outputs/025_lambda_flip_risk_separability/report.md) · [独立审计](reviews/025_lambda_flip_risk_separability.md)。

**024阶段记录（2026-09-19）：** 执行及评价完成，快速独立审计PASS，可冻结／结项。DeepSeek/Qwen均方向支持、均未达强迁移证据门槛；3515/3516核心有效，费用及未知预留57.534444/80元。固定λ=2、模型、prompt和API-BGE C48均未改，不使用reserved40。旧暂停及解析修订均保留。[主报告](outputs/024_lambda2_transfer_validation/report.md) · [独立审计](reviews/024_lambda2_transfer_validation.md)。023不自动启动024为此前边界，本次由用户另行授权；API路由和预算政策不变。


**当前023：** 023完成固定λ=2的零API响应/敏感性分析，快速独立审计PASS，可冻结／结项。019/020两轮在约1.946–2.079的标签平台内完全不变，±0.05无改判；较宽近性能区域有重叠，但峰位跨轮漂移，false-S随λ增大。固定λ=2未改，无新winner、不启动024或reserved40。[中文主报告](outputs/023_lambda_boundary_response_analysis/report.md) · [Figure 1](outputs/023_lambda_boundary_response_analysis/figures_001/figure1_performance.pdf) · [独立审计](reviews/023_lambda_boundary_response_analysis.md)。

**当前022：** 022完成零API阶段A：16名development患者1529条R0＋879条R1折外评分，竞争感知与学习全局λ的2408条标签完全相同；相对U2正确数R0−28、R1−13，false-S虽减少但PA/MCC未达门槛。停止B/Qwen，保留λ=2；新增费用0/80元，快速独立审计PASS，可冻结／结项。[中文主报告](outputs/022_competition_aware_support_calibration/report.md) · [独立审计](reviews/022_competition_aware_support_calibration.md)。

**此前已审状态：019–021快速独立审计PASS，可冻结／结项。** 019原低false-S保护门槛失败；020固定λ2在最后10名development患者879条上取得双轮总体PA/MCC正向结果，但有false-S增加、NS损失及LLM不稳定；021本地BGE可运行但严格等价FAIL（全本地reference一致565/879），不能继承020成绩。

历史019–022边界：40名development均已使用；reserved未用于这些阶段。现状为036已完成reserved最终评价，不再用于开发。U2离线改判未同步改写原reason，尚非可直接部署的完整核验器。

| 当前任务 | 正式结果 | 独立审计 |
|---|---|---|
| 019：支持边界筛查 | [主报告](outputs/019_support_boundary_screen/report.md) | [PASS，原门槛失败](reviews/019_support_boundary_screen.md) |
| 020：固定λ2确认 | [主报告](outputs/020_lambda2_patient_validation/report.md) | [PASS，development确认](reviews/020_lambda2_patient_validation.md) |
| 021：BGE本地化 | [主报告](outputs/021_bge_localization/report.md) | [PASS，严格等价FAIL](reviews/021_bge_localization.md) |
| 022：竞争感知校准 | [主报告](outputs/022_competition_aware_support_calibration/report.md) | [PASS，阶段A停止](reviews/022_competition_aware_support_calibration.md) |

阅读入口：[项目总览](docs/PROJECT_STATUS.md) · [API当前规则](docs/API_POLICY.md) · [环境与安全重放](docs/REPRODUCIBILITY.md) · [审计索引](reviews/README.md)。

022按模型分流：BGE继续硅基流动冻结缓存，Judge直接阿里云0731，不等待池耗尽；全任务累计80元。022已停止，不自动新增调用。历史报告／协议／旧CURRENT中的“待审、旧路由、患者余量、未改.gitignore”是冻结快照；当前状态以本页、PROJECT_STATUS和各任务CURRENT_STATUS为准。

基于 VeriFact-BHC 的患者级临床文本与电子病历记录一致性核验研究。

当前研究围绕临床文本事实核验展开：给定一份关于患者的临床文本，利用该患者已有的电子病历（EHR）记录判断文本中的陈述是否得到病历支持，并分析现有核验方法的失败模式及可能的改进方法。

---

## 1. Project Structure

```text
Research-VeriFact/
├── data/       # 原始数据及研究过程中产生的需要持久化存储的数据
├── docs/       # 外部参考资料、阅读笔记和历史研究资料
├── reviews/    # 独立审计意见、修订与结项记录
├── src/        # 可复用的正式代码
├── scripts/    # src代码的运行入口
├── tasks/      # 各项研究任务的设计与说明
├── outputs/    # 各项任务对应的运行结果，与tasks一一对应
├── environment.yml  # Conda 环境定义
└── tests/      # 自动化测试
```

### `data/`

研究数据。

当前建议的数据层级：

```text
data/
├── 00_raw/
└── 01_interim/
```

- `00_raw/`
  - 保存官方发布的原始数据。
  - 保持只读，不修改其中任何文件。
  - 当前 VeriFact-BHC 数据位于：

    `data/00_raw/verifact-bhc/1.1.0/`

  - 官方数据定义参见该目录中的 `README.md`；本地 release 的实际结构、覆盖及说明差异参见 [数据审计结果](outputs/001_dataset_audit/README.md)。

- `01_interim/`
  - 保存从原始数据生成的中间数据。
  - 包括表连接、筛选、格式转换、统计分析所需的派生数据等。
  - 可确定性生成的内容原则上应能够由原始数据和代码重新生成。
  - 对于外部模型/API 等无法保证完全重现的中间结果，应保留原始响应及必要的运行信息。

如以后确实需要区分更多稳定的数据层，再增加新的数据目录，不提前建立不需要的层级。

### `docs/`

外部研究资料与阅读笔记。

论文、补充材料等外部来源主要保存在：

`docs/sources/`

这里不保存程序运行结果。

| 资料 | 定位 |
| --- | --- |
| [数据集笔记](docs/数据集笔记.md)、[论文笔记](docs/论文笔记.md) | 用户原始学习笔记，保留原内容；核验结论以 001–003 正式成果为准 |
| [患者 5954 中文导读](docs/VeriFact-BHC_单病例中文导读_患者5954.md) | 早期教学案例，患者已纳入 003 探索组 |
| [动态切分提示词](docs/动态切分提示词.md) | 之前 Hospital-02 项目的经验记录，不是当前 VeriFact 的方法或实验成绩 |
| `docs/sources/verifact_upstream_f115d36cb65f/` | 002 下载的作者代码参考快照；来源为 philipchung/verifact，固定提交和文件哈希见目录内 source_manifest.json 与 additional_source_manifest.json，未执行其模型或分析脚本 |

### `reviews/`

保存 [独立审计记录及后续状态](reviews/README.md)。原审计意见、执行者修订自查、用户确认结项分别记录；任务完成不意味着数据异常已消失，也不等于新增医学裁决。

### `src/`

项目的可复用代码。

正式实现的数据读取、检索、核验、评价等逻辑应逐步放入 `src/`，而不是长期堆积在单个脚本中。

当前已采用 Python 包结构：

```text
src/
└── verifact_research/
    ├── audit/       # VeriFact-BHC 数据审计
    └── evaluation/  # baseline 与新方法共用的评价及论文复算
```

审计入口为 `scripts/audit_dataset.py`，关键逻辑测试位于 `tests/test_dataset_audit.py`。

### `scripts/`

项目的运行入口。

例如：

- 数据检查；
- 数据预处理；
- 运行模型；
- 执行检索；
- 计算评价指标；
- 生成分析结果。

`scripts/` 中的代码应尽量调用 `src/` 中的实现，而不是重复实现核心逻辑。

### `tasks/`

记录研究过程中相对独立的工作任务。

当前任务目录按执行顺序编号：

```text
tasks/
├── 001_dataset_audit/
├── 002_reproduce_paper_results/
├── 003_error_analysis/
├── 004_event_alignment_pilot/
└── ...
```

这里的 `task` 不要求一定是论文中的“实验”。

数据核验、探索性分析、baseline、错误分析、方法实验和消融实验都可以作为独立 task。

每个 task 可以包含自己的 `README.md`，特别简单的可以不写，用于记录：

- 为什么进行这项任务；
- 要回答什么问题；
- 使用什么输入；
- 计划采用什么方法；
- 如何评价；
- 当前状态；
- 得到了什么结论。

任务编号一旦建立，不因任务失败、废弃或研究方向变化而重新编号。

### `outputs/`

保存各 task 实际产生的结果。

`tasks/` 和 `outputs/` 使用相同的编号和名称，一一对应：

```text
tasks/
└── 003_error_analysis/

outputs/
└── 003_error_analysis/
```

如果同一个 task 被运行多次，应保留不同运行记录，避免覆盖历史结果，例如：

```text
outputs/
└── 003_error_analysis/
    ├── run_001/
    │   └── review_004/  # 现行修订报告；此前 review 也保留
    ├── run_002/
    │   └── review_003/  # 同一修订的重复生成结果
    └── verification_003/
```

每次正式运行应尽可能保留能够复现该结果的信息，例如：

- 实际运行参数；
- 模型及版本；
- 输入数据版本；
- 随机种子；
- predictions；
- metrics；
- logs。

### `tests/`

项目自动化测试。

用于检查重要的数据处理逻辑、评价指标和公共函数，防止后续修改代码时无意改变已有行为。

---

## 2. Data Rules

### Raw data is immutable

`data/00_raw/` 中的官方数据不得直接修改。

需要清洗、筛选、合并或增加字段时，应生成新的派生文件，而不是覆盖原始数据。

### Derived data should be reproducible

研究过程中生成的数据原则上应能够根据以下内容重新构建：

1. 原始数据；
2. 当前代码；
3. 对应配置或参数。

### Use relative project paths

代码中不要写死：

`D:\Research-VeriFact\...`

应尽量使用相对于项目根目录的路径，使项目迁移到其他位置后仍然可以运行。

---

## 3. Task and Output Convention

一个研究工作如果值得单独记录其目的、输入、过程或结果，就可以建立一个 task。

任务编号示例（完整当前状态见第5节）：

```text
001_dataset_audit
002_reproduce_paper_results
003_error_analysis
004_event_alignment_pilot
```

004 已完成真实执行、独立审计及修订定向复核（2026-09-14 PASS），具备正式冻结／结项条件；结果方向不一致与执行遵守有限等研究边界继续保留。

无需判断它是否属于严格意义上的“实验”。

对应输出使用完全相同的名称：

```text
tasks/003_error_analysis/
outputs/003_error_analysis/
```

`tasks/` 记录“为什么做、准备怎么做”。

`outputs/` 记录“实际跑出了什么”。

---

## 4. Current Dataset

当前主要数据集：

**VeriFact-BHC v1.1.0**

位置：

`data/00_raw/verifact-bhc/1.1.0/`

主要数据包括：

- BHC propositions；
- clinician verdicts；
- proposition validity annotations；
- patient reference EHR；
- VeriFact model verdicts；
- retrieved reference contexts；
- model / retrieval configuration metadata。

官方定义参见 [release README](data/00_raw/verifact-bhc/1.1.0/README.md)。实际文件与说明存在部分差异，已在 [数据审计报告](outputs/001_dataset_audit/run_006/report.md) 中分别标明官方声明、独立验证结果和待确认事项。

---

## 5. Current Status

现行结论见页首和[项目总览](docs/PROJECT_STATUS.md)。以下为001–035阶段索引，旧“reserved尚未开启”等表述仅适用于该历史阶段；036以后状态不能据此回退。

034/035已快速独立审计PASS：同ID比较及λ/温度分析可冻结，当前环境启动方式见RUN_ENVIRONMENT。033已快速独立审计PASS：未找到稳定同风险更优subset，A3小幅工作点收益保留，A全40仅为保守覆盖策略。032已快速独立审计PASS：双粒度主方案PA略升但MCC下降、false-S增加，未实现共同提高，不改选辅助方案、不自动033。031已快速独立审计PASS：扩充未带来实质确认增量，停止当前新增信息Gate，A仅作简单参照，不自动032。030已快速独立审计PASS：训练规模有积极线索，组成敏感性未解决，不能确定稳定最低人数，不自动扩量或031。029已快速独立审计PASS：保留联合信息的有限OOF增量，迁移未稳定复现，不选winner、不自动030。028已快速独立审计PASS：trace仅保留44/110真S救回，未过门槛，停止当前版本，不自动029。027离线诊断已快速独立审计PASS：高rescue区不能只靠换阈值恢复原门槛，现有证据不支持继续救当前Gate。026结论保持：冻结SD跨患者组迁移未达事前门槛，停止当前版本。025此前结论保持：E路线停止，第二Judge仅保留有限开发线索，完整门槛无winner。024已完成跨后端/模型开发验证；均方向支持、未达强证据门槛。固定λ2保持，reserved40未开启。022此前按阶段A门槛停止，023完成零API敏感性分析。此前021已完成两个BGE的本地化与API→本地冻结等价性检查；严格等价门槛FAIL，因此020的科学结果仍属于原API-BGE实现条件，不能自动继承到本地链路。001–035均有相应独立审计依据。40名development均已用于开发/确认；021仅复用020冻结development输入，40名reserved test继续保留，是否开启最终测试及采用API还是本地BGE需另行冻结决策。

| 任务 | 状态 | 说明与结果 |
| --- | --- | --- |
| `001_dataset_audit` | 已完成（2026-09-12） | [任务说明](tasks/001_dataset_audit/README.md) · [正式结果入口](outputs/001_dataset_audit/README.md) |
| `002_reproduce_paper_results` | 已完成（2026-09-13） | [任务说明与统一协议](tasks/002_reproduce_paper_results/README.md) · [正式结果入口](outputs/002_reproduce_paper_results/README.md) |
| `003_error_analysis` | 已完成并确认结项（2026-09-13） | [任务说明](tasks/003_error_analysis/README.md) · [结果入口](outputs/003_error_analysis/README.md) |
| `004_event_alignment_pilot` | 已完成，修订独立复核 PASS，可冻结／结项（2026-09-14） | [任务说明](tasks/004_event_alignment_pilot/README.md) · [中文主报告](outputs/004_event_alignment_pilot/run_003/analysis/report.md) |
| `005_pilot_effect_analysis` | 已通过独立审计（2026-09-14；见 reviews/005） | [任务说明](tasks/005_pilot_effect_analysis/README.md) · [简明中文主报告](outputs/005_pilot_effect_analysis/run_002/review_002/report.md) |
| `006_source_context_feasibility` | 已通过精简独立审计（2026-09-14；见 reviews/006） | [任务说明](tasks/006_source_context_feasibility/README.md) · [简明中文主报告](outputs/006_source_context_feasibility/run_001/review_001/semantic_001/report.md) |
| `007_context_retrieval` | 已通过精简独立审计（2026-09-14；见 reviews/007） | [任务说明](tasks/007_context_retrieval/README.md) · [简明中文主报告](outputs/007_context_retrieval/run_001/review_001/semantic_001/report.md) |
| `008_retrieval_planning` | 已通过精简独立审计（2026-09-14；见 reviews/008） | [任务说明](tasks/008_retrieval_planning/README.md) · [简明中文主报告](outputs/008_retrieval_planning/run_001/report.md) |
| `009_retrieval_baselines` | 修订独立复核 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/009_retrieval_baselines/README.md) · [简明中文主报告](outputs/009_retrieval_baselines/report.md) |
| `010_verifact_baseline_alignment` | 精简独立审计 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/010_verifact_baseline_alignment/README.md) · [简明中文主报告](outputs/010_verifact_baseline_alignment/report.md) |
| `011_evidence_integrity_packaging` | 执行完成，pilot未过继续门槛；独立审计PASS，可结项 | [任务说明](tasks/011_evidence_integrity_packaging/README.md) · [中文主报告](outputs/011_evidence_integrity_packaging/report.md) |
| `012_comparative_error_diagnosis` | 独立审计 PASS，可冻结／结项（2026-09-15） | [任务说明](tasks/012_comparative_error_diagnosis/README.md) · [中文主报告](outputs/012_comparative_error_diagnosis/report.md) |
| `013_multi_mechanism_screen` | 独立审计PASS，四分支停止，可结项 | [任务说明](tasks/013_multi_mechanism_screen/README.md) · [中文主报告](outputs/013_multi_mechanism_screen/report.md) |
| `014_qwen27b_baseline_comparison` | 修订独立复核PASS，可冻结／结项 | [任务说明](tasks/014_qwen27b_baseline_comparison/README.md) · [中文主报告](outputs/014_qwen27b_baseline_comparison/report.md) |
| `015_disagreement_adjudication` | 修订独立复核PASS，无winner，停止并结项 | [任务说明](tasks/015_disagreement_adjudication/README.md) · [中文主报告](outputs/015_disagreement_adjudication/report.md) |
| `016_disagreement_triggered_review_validation` | 快速独立审计PASS，未达门槛，停止并结项 | [当前任务入口](tasks/016_disagreement_triggered_review_validation/CURRENT.md) · [中文主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md) · [独立审计](reviews/016_disagreement_triggered_review_validation.md) |
| `017_verification_supervised_evidence_utility` | 快速独立审计PASS；第一阶段未达门槛，停止 | [任务](tasks/017_verification_supervised_evidence_utility/README.md) · [中文主报告](outputs/017_verification_supervised_evidence_utility/report.md) · [独立审计](reviews/017_verification_supervised_evidence_utility.md) |
| `018_verifact_gap_attribution` | 快速独立审计PASS；离线诊断结项 | [任务](tasks/018_verifact_gap_attribution/README.md) · [中文主报告](outputs/018_verifact_gap_attribution/report.md) · [独立审计](reviews/018_verifact_gap_attribution.md) |
| `019_support_boundary_screen` | 第一阶段完成，原低代价保护门槛未通过；快速独立审计PASS | [任务](tasks/019_support_boundary_screen/CURRENT_STATUS.md) · [中文主报告](outputs/019_support_boundary_screen/report.md) |
| `020_lambda2_patient_validation` | 固定λ=2新10名development患者双轮验证完成；总体PA/MCC复现改善，快速独立审计PASS | [任务](tasks/020_lambda2_patient_validation/CURRENT_STATUS.md) · [中文主报告](outputs/020_lambda2_patient_validation/report.md) · [统计附录](outputs/020_lambda2_patient_validation/statistics.md) |
| `021_bge_localization` | 两个BGE本地化完成；严格API→本地冻结等价FAIL，快速独立审计PASS | [任务](tasks/021_bge_localization/CURRENT_STATUS.md) · [中文主报告](outputs/021_bge_localization/report.md) · [当前状态](outputs/021_bge_localization/CURRENT_STATUS.md) |
| `022_competition_aware_support_calibration` | 阶段A停止；快速独立审计PASS | [任务](tasks/022_competition_aware_support_calibration/CURRENT_STATUS.md) · [报告](outputs/022_competition_aware_support_calibration/report.md) · [独立审计](reviews/022_competition_aware_support_calibration.md) |
| `023_lambda_boundary_response_analysis` | 离线响应分析完成；快速独立审计PASS；λ=2不变 | [任务](tasks/023_lambda_boundary_response_analysis/CURRENT_STATUS.md) · [报告](outputs/023_lambda_boundary_response_analysis/report.md) · [图](outputs/023_lambda_boundary_response_analysis/README.md) |
| `024_lambda2_transfer_validation` | 快速独立审计PASS；方向支持，未达强迁移证据门槛 | [任务](tasks/024_lambda2_transfer_validation/CURRENT_STATUS.md) · [报告](outputs/024_lambda2_transfer_validation/report.md) · [审计](reviews/024_lambda2_transfer_validation.md) |
| `025_lambda_flip_risk_separability` | 快速独立审计PASS；E停止，完整门槛无winner | [任务](tasks/025_lambda_flip_risk_separability/CURRENT_STATUS.md) · [报告](outputs/025_lambda_flip_risk_separability/report.md) · [审计](reviews/025_lambda_flip_risk_separability.md) |
| `026_frozen_sd_patient_transfer` | 快速独立审计PASS；冻结SD未达迁移门槛，停止 | [任务](tasks/026_frozen_sd_patient_transfer/CURRENT_STATUS.md) · [报告](outputs/026_frozen_sd_patient_transfer/report.md) · [审计](reviews/026_frozen_sd_patient_transfer.md) |
| `027_dual_judge_transfer_diagnosis` | 快速独立审计PASS；离线诊断结束，026停线保持 | [任务](tasks/027_dual_judge_transfer_diagnosis/CURRENT_STATUS.md) · [报告](outputs/027_dual_judge_transfer_diagnosis/report.md) · [审计](reviews/027_dual_judge_transfer_diagnosis.md) |
| `028_traceable_claim_evidence_verification` | 快速独立审计PASS；可追溯核查未过门槛，停止当前版本 | [任务](tasks/028_traceable_claim_evidence_verification/CURRENT_STATUS.md) · [报告](outputs/028_traceable_claim_evidence_verification/report.md) · [审计](reviews/028_traceable_claim_evidence_verification.md) |
| `029_semantic_information_gate` | 快速独立审计PASS；保留OOF信号，迁移未稳定，不选winner | [任务](tasks/029_semantic_information_gate/CURRENT_STATUS.md) · [报告](outputs/029_semantic_information_gate/report.md) · [审计](reviews/029_semantic_information_gate.md) |
| `030_gate_training_stability` | 快速独立审计PASS；规模有积极线索，组成敏感性未解决，不自动扩量 | [任务](tasks/030_gate_training_stability/CURRENT_STATUS.md) · [报告](outputs/030_gate_training_stability/report.md) · [审计](reviews/030_gate_training_stability.md) |
| `031_training_expansion_confirmation` | 快速独立审计PASS；扩充未确认实质增量，停止当前新增信息Gate | [任务](tasks/031_training_expansion_confirmation/CURRENT_STATUS.md) · [报告](outputs/031_training_expansion_confirmation/report.md) · [审计](reviews/031_training_expansion_confirmation.md) |
| `032_evidence_relation_correction` | 快速独立审计PASS；主方案未实现PA/MCC共同提高，不改选辅助方案 | [任务](tasks/032_evidence_relation_correction/CURRENT_STATUS.md) · [报告](outputs/032_evidence_relation_correction/report.md) · [审计](reviews/032_evidence_relation_correction.md) |
| `033_gate_training_subset` | 快速独立审计PASS；未找到稳定同风险更优subset | [报告](outputs/033_gate_training_subset/report.md) · [审计](reviews/033_gate_training_subset.md) |
| 034 | 同ID比较审计PASS；系统级比较非纯组件因果 | [当前状态](outputs/034_same_data_comparison/CURRENT_STATUS_002.md) · [报告](outputs/034_same_data_comparison/report.md) · [审计](reviews/034_same_data_comparison.md) |
| 035 | 边界/温度分析审计PASS；激活环境修复，标签不变NLL降低 | [当前状态](outputs/035_lambda_boundary_calibration/CURRENT_STATUS_002.md) · [报告](outputs/035_lambda_boundary_calibration/report.md) · [审计](reviews/035_lambda_boundary_calibration.md) |

审计代码、机器结果、原始文件校验和重复运行验证均已完成。审计保留了实际数据异常，其中两条医生第二轮记录触发一致性检查失败；任务完成不表示所有数据检查通过。详细异常和适用范围统一记录在审计结果中。

002 对 426 个模型/实验组合重评分，72 项核心点估计与论文一致；R1-70B 主配置的 MCC 置信区间仍有差异，正式附录部分未确认。两次完整运行的 37 个机器文件一致；002 完成时的 30 项测试与公共评价入口回放通过。

后续 baseline 和新方法统一使用 `scripts/evaluate_predictions.py` 与 `verifact_research.evaluation.evaluate`。默认 valid-only、固定队列、完整预测、三分类 PA/AC1/MCC 和患者 bootstrap；论文保留 invalid 的 item bootstrap 口径单独维护。具体样本与参数以 002 协议为准。

003 在 20 名探索患者的 1,817 条有效 atomic claims 中分层查看了 24 例，保留 40 名后续开发与 40 名测试患者。修订版 review_004 将观察收紧为事件对应和支持充分性问题；H03 撤回遗漏时间归因，H04 补充术语／检查对应及输入中已有异常信息。原 24 例的 R1 完整输出已复查，仍保留无法确定原因的病例；修订者自查完成，用户确认本任务结束。后续独立定向复核已 PASS，H03 阻塞项关闭，见 [003 审计末尾记录](reviews/003_error_analysis.md)；没有新增医生裁决。首个假设已完成004 pilot；003原第二个实验未按原方案单独执行，相关证据利用问题已在005–009继续分析，不是当前自动待办。003观察仍非已验证的方法贡献。

正式阅读入口分别为 001 的 `run_006`、002 的 `run_003`、003 的 `run_001/review_004`、004 的 `run_003/analysis/report.md`。003 完成时全项目 42 项测试通过，记录见 [003 verification_003](outputs/003_error_analysis/verification_003/verification.json)。004 离线准备时 54 项测试通过，记录见 [004 verification_001](outputs/004_event_alignment_pilot/verification_001/verification.json)。004 真实运行的执行自查、原始回执重复评价和测试见 [verification_live](outputs/004_event_alignment_pilot/verification_live/run_001/verification.json)，不等同于独立审计。004 修订后的独立复核见 [审计文末结论](reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)：81 项现有测试通过、41 项隔离篡改检查通过，两次离线重放的 15 个结果文件均与原结果逐字节一致。

后续任务复用冻结的患者分组清单，不重新抽组。baseline 和新方法继续使用 002 的同一评价代码。任务结束后，001 的数据异常、002 的论文差异和代码使用限制、003 的探索性结论边界仍保留，详见 [审计与后续状态](reviews/README.md)。

---

## 6. Development Environment

项目使用 Conda 环境 `research-verifact`（Python 3.11），环境定义见 `environment.yml`。

```powershell
conda env create -f environment.yml
conda activate research-verifact
```

已有环境可用 `conda env update -f environment.yml` 同步依赖。

029–031使用独立research-verifact-029环境，版本冻结见其preparation_001/environment.json；原环境未改。当前计算环境支撑001–028的数据处理、评价和既有回执重放；021本地GPU环境另见[environment.local-bge.yml](environment.local-bge.yml)及[复现说明](docs/REPRODUCIBILITY.md)。DuckDB 读取数据，pypdf 读取论文，fonttools 保留为 001 已登记的字体编码核对工具，NumPy/pandas/SciPy/scikit-learn/irrCAC 支持计算及指标交叉核验。003、004 复用现有依赖，没有新增模型推理包；版本以 `environment.yml` 为准。001–003 的日常重跑及 004 离线准备、已保存响应重评分不需要 GPU 或推理 API。004 真实推理由 Python 标准库 urllib 调用硅基流动，无新增依赖；虚构服务 preflight 也会真实调用 API。

2026-09-14 状态同步核对：Python 为 3.11.16，8 个固定依赖版本均与环境定义一致，`python -m pip check` 通过。004 的 SiliconFlow 请求仅使用标准库，当前环境没有 Groq 专属依赖，不新增包或升级版本，`environment.yml` 无需变化。fonttools 虽未被当前解析函数直接导入，仍由 001 runner 查询并记录其版本，因此本轮不移除这一已登记依赖。重新渲染 002 的来源核对 PNG 另需 Poppler 的 `pdftoppm`，不属于日常重跑依赖，见 [来源核对说明](outputs/002_reproduce_paper_results/source_review/README.md)。

---

## 7. Run Dataset Audit

从项目根目录、已激活的 `research-verifact` 环境运行：

```powershell
python -B scripts/audit_dataset.py
python -B -m unittest discover -s tests -v
```

审计创建新的 `outputs/001_dataset_audit/run_XXX/`，保留历史结果。当前 release 的第二轮医生字段矛盾会使审计返回非零退出状态，完整结果仍会生成，manifest 标为 `failed_checks`；运行异常则标为 `error`。具体检查与参数见 [任务说明](tasks/001_dataset_audit/README.md)。

---

## 8. Reproduce Paper Results and Evaluate Methods

```powershell
python -B scripts/reproduce_paper_results.py
python -B scripts/evaluate_predictions.py --help
```

论文复算使用已有 release 预测，不调用推理服务，每次创建新的 002 run。baseline / 新方法评价 CSV 格式、完整命令、缺失处理和配对比较见 [002 任务说明](tasks/002_reproduce_paper_results/README.md)。

---

## 9. Review Error Analysis Results

003 已结项，先阅读 [结果入口](outputs/003_error_analysis/README.md) 或 [现行报告](outputs/003_error_analysis/run_001/review_004/report.md)。

核对已保存的两份修订成果、原始文件哈希、链接和现有测试：

```powershell
python -B tasks/003_error_analysis/verify.py
```

该命令新建 verification 记录，不重新抽患者或调用模型。重新生成报告的命令、review 序号和完整输出阅读范围见 [003 任务说明](tasks/003_error_analysis/README.md)。

---

## 10. Event Alignment Pilot Results

004 按冻结顺序使用 6 名开发患者、421 条有效 atomic claims，三臂由硅基流动 `deepseek-ai/DeepSeek-V4-Flash` 使用同一完整 reference 生成。1,263 个逻辑请求均已处理，1,262 个有效预测，另有 1 个 LLM routine 截断失败；对应 routine 比较受阻。核心 event_alignment − structured 使用完整 181/240 分母，MCC 差值分别为 +0.0425/-0.0416，患者 bootstrap 区间均跨 0。检查结构遵守有限，不建议直接扩大当前版本。AWS Bedrock / Groq 已放弃，不是当前待办。真实推理按 usage 和公开日期价格估算约 ¥30.326；用户反馈本轮消耗约 30 元额度，尚未逐笔核对账单。后续实验须控制输入 token 与调用成本。

```powershell
python -B tasks/004_event_alignment_pilot/analyze_live.py --run outputs/004_event_alignment_pilot/run_003 --output outputs/004_event_alignment_pilot/replay_local --no-report
python -B tasks/004_event_alignment_pilot/verify_live.py --run outputs/004_event_alignment_pilot/run_003
```

以上命令只重放本地记录，不发送临床内容，输出目录须不存在。直接阅读 [004 中文主报告](outputs/004_event_alignment_pilot/run_003/analysis/report.md)；配置、服务恢复、评价处理与机器资料见 [004 任务说明](tasks/004_event_alignment_pilot/README.md) 和 [输出索引](outputs/004_event_alignment_pilot/README.md)。历史 run_001/run_002 离线准备保留。当前修订已通过 [独立定向复核](reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)，两项原问题关闭，可正式冻结／结项。执行者的修订、自查和交审版本保存在 [历史修订说明](outputs/004_event_alignment_pilot/verification_live/run_002/README.md)。旧报告、status.json 和 verification 中的“等待审计／复核”保留其生成时状态，当前状态以本入口和审计末尾追加结论为准。后续 API 费用确认按 [当前规则](AGENTS.md#api-调用费用与确认规则)：一次新任务预估总费用不超过 80 元可直接执行，超过则先确认；历史 run 的授权与预算保留原记录。

## 11. API账号、平台与费用（现行）

执行前读取[API_POLICY.md](docs/API_POLICY.md)和[AGENTS费用规则](AGENTS.md#api-调用费用与确认规则)。新任务默认80元累计保护；≤80元直接执行，超过或无法合理估算先确认，跨模型、账号、供应商、阶段和重试累计。

后续收费API（含V4/Qwen）先使用硅基流动启用号池，从account_2起按编号换号。所有启用硅基流动账号明确额度耗尽后，通知用户并永久记录此次转换，后续全部API工作转阿里云，除非用户另有指示。超时／503不当作额度耗尽，目前未确认全部耗尽。

本地密钥位置：`.env.siliconflow_pool`与`.env.aliyun`，现有.gitignore已排除，勿提交或打印。配置与实现边界见[硅基流动说明](docs/siliconflow_pool/README.md)、[阿里云当前说明](docs/aliyun/CURRENT.md)。单次工具、历史runner和研究任务的冻结预算须区分；旧016的40元硬保护及全部回答不改写，新任务另行登记80元上限。此次同步不调用API、不查询余额、不重新启动历史任务。

以下第12–23节回顾各任务形成时的发现与建议，不是新的执行授权；当前状态以顶部总览和审计索引为准。

## 12. Pilot Effect Analysis

005 对 004 全部 421 条进行转移统计，并深入阅读 25 个改善、退化、仍错及稳定对照病例。两臂指标未变化，没有新推理；观察涉及命题要求、证据利用、标签边界及来源上下文中的事件/剂量指代。005当时建议验证局部来源上下文与EHR证据的角色区分，006已完成该验证且未证明净收益；不作为新的待执行实验。阅读 [唯一中文主报告](outputs/005_pilot_effect_analysis/run_002/review_002/report.md)；104 项测试、重复提取/渲染及 265 处锚点自查见 [结果入口](outputs/005_pilot_effect_analysis/README.md)。

## 13. Source Context Feasibility

006 在用户批准的 8 元上限内完成 64 条命题、三臂 192 次实际尝试，189 条有效预测；2 次通信未知和 1 次截断未重发、未补标签。两个作者的主比较均受缺失阻塞，human 来源−重复对照 ΔMCC +0.0326、区间跨 0，且 NS/NA 召回下降。深读 28 例后建议修改切入点，先考察固定命题下 EHR 证据来源/时段与支持范围，不直接扩大当前 BHC 上下文版本。费用与未知预留约 ¥3.8661；116 项离线测试、已有回执重放及 316 处锚点自查见 [006 结果入口](outputs/006_source_context_feasibility/README.md)，主报告为 [report.md](outputs/006_source_context_feasibility/run_001/review_001/semantic_001/report.md)。005 最新独立结论以 [005 审计](reviews/005_pilot_effect_analysis.md) 为准，原报告保留历史状态。

## 14. Context-aware Retrieval

007 使用四名新的开发患者、96 条固定有效 claim，比较 BM25 的 claim、来源句、局部来源、claim＋局部来源融合查询；最终 Judge 仅收到原 claim 和 EHR。392 次主试验/重复对照及 12 次零预算边界补充均有效，累计估算 ¥4.1703。主 mixed−claim ΔMCC 为 LLM +0.0089、human −0.0718，两个患者区间均跨 0；真实召回改善与同输入 Judge 波动、查询偏离及证据截取问题并存。007当时建议改进候选召回/组织及原claim重排；008–013已开展后续对照，不能把该建议当新的自动待办。阅读 [唯一中文主报告](outputs/007_context_retrieval/run_001/review_001/semantic_001/report.md)；124 项断网测试、回执重放及 377 处锚点自查见 [结果入口](outputs/007_context_retrieval/README.md)。006 最新独立结论见 [精简审计](reviews/006_source_context_feasibility.md)，历史报告保留生成时状态。

## 15. LLM Retrieval Planning

008 在六名新开发患者的 144 条固定 claim 上比较 direct、简单来源扩展和 LLM planner，共用 BM25＋BGE-M3、原 claim rerank 和普通 structured Judge。三臂各 144 条有效预测，311 个实际 Judge 请求（含 12 次无翻转重复），全部服务共 684 次，usage 估算 ¥4.1528＜¥40。Planner−direct 的 ΔMCC 为 LLM +0.0176、human 0，区间均跨 0；100 个计划使用、44 个退回，接口损耗不均衡。20 例完整阅读表明局部证据补充与丢失并存，008当时建议检查候选融合/证据覆盖和Judge支持边界；009–013已进一步检验，当前仍不扩大通用planner。阅读 [唯一中文主报告](outputs/008_retrieval_planning/run_001/report.md)；离线重建、费用、79 处锚点和准确交审版本见 [结果入口](outputs/008_retrieval_planning/README.md)。007 的当前独立状态以 [精简审计](reviews/007_context_retrieval.md) 为准，历史报告不回写。

## 16. Retrieval Baselines and Evidence Loss

009先用008旧患者开发，再冻结A48（BM25+dense RRF）、B48（dense）和C48（两路交替保留48候选），在原开发顺序第19–24名患者全部650条valid claim确认。三臂共享原claim重排、Judge与证据上限，均完整。C−A的LLM/human ΔMCC为+0.0002/+0.0158，未证明稳定优势；B在人写组净少判对20条。证据损失同时出现于候选门槛、每note限制、字符容量和Judge解释；这是009当时的后续研究依据，010–013已完成相关校准与筛选，当前不继续原样扩大。全任务usage估算¥18.0822＜¥40；首次自查143项测试通过，修订后146项通过，原回执重放不变。阅读[唯一主报告](outputs/009_retrieval_baselines/report.md)及[成果与当前审计状态](outputs/009_retrieval_baselines/README.md)，自查不等于独立审计。008当前独立结论以[审计记录](reviews/008_retrieval_planning.md)为准，历史报告保留原状态。

009当前状态以[独立审计末尾追加](reviews/009_retrieval_baselines.md)为准：146项断网测试、109个内容文件重放及冻结材料负向检查通过；旧报告、自查和交审说明保留当时状态。

## 17. 010 baseline校准（精简独立审计PASS，可结项）

010 已完成同队列发布系统参考及同期同Judge的reference校准，2026-09-15精简独立审计PASS，可冻结／结项；沿用009的650条命题，没有新患者。发布reference−C48的LLM/human ΔMCC为−0.0572/−0.0497，两个区间跨0，human PA/AC1区间倾向C48；发布系统较高PA不能直接归因于检索。保留C48作实用对照，010当时建议单独验证检查身份、条件句和时间/状态完整性；尚未证明packaging有效。主报告见[010成果入口](outputs/010_verifact_baseline_alignment/README.md)，独立结论见[010审计记录](reviews/010_verifact_baseline_alignment.md)，历史报告保留交审时状态。

同期两臂各650条有效预测，预设重复24次中2次翻转；旧009→010相同C48完整输入有80/650条标签变化，不能将跨运行变化当reference收益。全任务usage估算¥23.3621，未知请求保留¥0.1050，总已用/预留¥23.4671＜¥40，非账单。150项断网测试通过，009的3317个历史文件未变。010未更改C48、Judge或开发包装方法；全部调用停止，独立审计已通过，研究限制保留。

## 18. 011证据完整性验证（精简独立审计PASS，可冻结／结项）

011在既有任务基础上完成650条离线完整性/预算检查和固定24条三臂三次诊断，2026-09-15精简独立审计PASS，可冻结／结项；预设继续门槛未通过，650条main未启动。011的C−B三轮净正确数为−1/0/0、B−A为−2/0/0，停止当前B/C组合扩展，不把B整体改作新性能baseline。继续保留冻结C48作为实用对照；基本完整性确有修复，但未证明额外结构恢复有重复净收益。011当时40名开发只使用前24名，剩余16名及40名reserved test未用于011。当前入口：[011主报告](outputs/011_evidence_integrity_packaging/report.md)与[交审说明](outputs/011_evidence_integrity_packaging/audit_handoff.md)。

实际195个有效请求、usage估算¥1.2874。较完整的证据可伴随预算挤占，Judge的支持范围/NS-NA边界和重复波动仍明显。未将已发现的真实原文修复包装为方法有效；未启动main，后续012/013已开展诊断与机制筛选，当前仍不续跑011 main。

011当前独立结论见[审计记录](reviews/011_evidence_integrity_packaging.md)；原报告与交审快照保留当时状态。

## 19. 012对照错误诊断（独立审计PASS，可结项）

012_comparative_error_diagnosis 已完成离线执行并通过2026-09-15独立审计，可冻结／结项；[唯一主报告](outputs/012_comparative_error_diagnosis/report.md)。复用010同650条三组材料，错误并集195、固定深读24例（19条错误、5条三组共同正确），其余176条错误本轮未深读；0 API、无新患者。新增观察是本地极性/候选/打包损失与原/现系统共同的目标及支持范围问题并存，不能把正确标签或模型解释当机制证明。012建议优先验证目标/支持范围约束，极性与条件保真作为窄工程前提；保留冻结C48对照，不直接采用011 B或继续其main。建议有诊断依据但不是已证实优化收益。

012当前独立结论见[审计记录](reviews/012_comparative_error_diagnosis.md)：无阻塞项，可冻结／结项。原报告／交审快照保留当时状态；阅读缓存是保留metadata、空白规范化后相同正文的复用，并非所有块逐字节相同。

## 20. 013多机制筛选（独立审计PASS，可结项）

013_multi_mechanism_screen 已完成执行并通过2026-09-15快速独立审计，可冻结／结项；[唯一主报告](outputs/013_multi_mechanism_screen/report.md)。四个分支通过局部机制检查，但在固定231条压力集相对同期冻结C48的净正确数分别为：主谓合同−12、前缀修复−4、扩候选−5、LLM集合选择−5，均未通过预设门槛。停止当前四个实现的扩大，不默认组合；没有新患者确认或新论文方法候选。保留C48作既有实用对照，013当时剩余16名development与40名reserved test未用于013。全任务估算/预留¥18.8002，全部API已停止；局部作用、原文质量要求与整体性能结论应分开。

## 21. 014固定证据模型比较（修订独立复核PASS）

旧6名开发患者650条，同C48和structured，Qwen与010已有V4比较；两者非同期。Qwen可保留为较小模型研究对象，但human NA较弱，未证明非劣或本地部署性能。见[主报告](outputs/014_qwen27b_baseline_comparison/report.md)及[审计](reviews/014_qwen27b_baseline_comparison.md)。

## 22. 015双候选理由仲裁（修订独立复核PASS，停止）

主仲裁523/650，比最强单模型527净−4；evidence_only对照542只是探索性正向信号，后由016验证。015没有winner，不追加v2/v3；候选顺序偏差保留。见[主报告](outputs/015_disagreement_adjudication/report.md)及[审计](reviews/015_disagreement_adjudication.md)。

## 23. 016分歧触发独立复核（独立审计PASS，停止）

新6名开发患者601条，92条分歧；review452，低于Qwen457，只比普通repeat451多1条。原继续门槛未通过，human NA及患者保护亦有损失；停止当前方向，不以局部MCC提升挽救。未使用余下10名开发患者或reserved test确认。Qwen混合供应商、基础模型跨时段，限制保留。见[当前成果入口](outputs/016_disagreement_triggered_review_validation/CURRENT.md)、[主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)及[审计](reviews/016_disagreement_triggered_review_validation.md)。

## 24. 017医生verdict监督的证据utility（第一阶段停止，独立审计PASS）

017完成12名已暴露患者192条GT盲证据干预：19条稳定错误中稳定救回0条，160条稳定正确中破坏3条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。有限单段替换结果不是全局selection不可能性的证明。1572份有效回答，累计费用估算与未知预留¥13.37319060/¥80；原始回执、失败与历史001–016保持。见[017中文主报告](outputs/017_verification_supervised_evidence_utility/report.md)。
