# 研究问题—方法—证据—限制对应表

本轮主文是[完整中文稿](manuscript_zh.md)。以下按论点组织，不将任务编号作为论文主线。源报告保持历史字节，新的解释只在091。

|研究问题/论文位置|方法或比较|最关键证据|数据与源码入口|可以主张|不能主张|
|---|---|---|---|---|---|
|RQ1，§5.1|同一评分U0→固定U2；Gate及标准校准|3571条净+177、false-S+123；Gate净−22/false-S−63；StdM/V更高总分|[036正式报告](../036_final_validation/report.md)、[036方法](../036_final_validation/methods_and_settings.md)、tasks/019_support_boundary_screen/common019.py、src/verifact_research/evaluation/|早期非thinking冻结边界有确认性收益和代价|当前T-S＋PriorG/P90已在reserved最终验证；λ2是新最优算法|
|RQ2，§5.2|推理模式、评分接口、prior-only/G拆分及作者证据桥接|384条当前321/原作者310；prior-only与PriorG逐例相同；192证据桥接无明确质量增量|[078报告](../078_component_ablation/report.md)、[逐例复算](historical_anchor_checks.json)、tasks/078_component_ablation/analyze078.py、postprocessing_frozen.json|开发阶段组合增量；C48长度/成本价值|G与prior是两个独立有效组件；C48已证明精度优势或非劣|
|RQ2，§5.3、附录A|固定F4对称适配、训练选择、共享校准、理由特征|079新G净−3；080选中净−7；082新180净0/false-S+7；083NS召回5.6%|[079](../079_f4_priorg_adaptation/report.md)、[080](../080_final_decision_adaptation/report.md)、[081](../081_gt_blind_evidence_selection/report.md)、[082](../082_anchor_configuration_adaptation/report.md)、[083](../083_native_rationale_information/report.md)|测试过的适配没有稳定增加最终效用，保留备选点值与类别代价|所有校准/理由都无信息；事后挑未选候选冒充主成功|
|RQ2，§5.4|同期B/F4、CL4/X4及受控Judge替换|084净+6；087F−X+3兼有X损伤；085raw净+13而最终对默认仅+1且风险增|[084](../084_f4_coverage_validation/report.md)、[087](../087_f4_evidence_intervention/report.md)、[085正式报告](../085_r1_70b_valdemardi/report_formal.md)、final_system_comparison.json|示例和模型改变输出分布，效用依赖类别和决策层|原VeriFact精确checkpoint/完整pipeline复现；错配损伤全等于正向教学|
|RQ3，§5.5|090统一167共同core的raw/U0/U2/prior-only/G及四状态路径|raw120→127，final135→137；7−4−1+2−2=2；类对AUC未一致提升|[B_diagnosis](B_diagnosis.json)、[路径](B_case_paths.jsonl)、tasks/091_integrated_evidence_decision_study/diagnose091.py、tasks/087_f4_evidence_intervention/common087.py|精确解释已观察到的输出和边界变化|P学会特定医学推理；重新拟合必有效；新阈值最优|
|RQ3，§5.6|患者、时间块、固定重复与同体桥接|raw6胜/1负/15平；082重复24条无NS；090历史桥接7患者，P无重复|[历史核查](historical_anchor_checks.json)、[同体桥接](B_repeat090.json)、repeat091.py|单患者不是全部raw信号来源；具体已有重复边界|P已稳定复现；不同模型/输入的回答当同体重复；无重复即无效|
|RQ3，成本|同批usage、时延与完整/压缩/无示例对照|P比F输入−34.93%、费用−21.64%，未比B有整体优势|[090成本](../090_demo_constructor_repair_validation/cost_ledger.json)|相对F的实测成本取舍|端到端加速、免费检索、模型租赁成本已核实|
|RQ4，§5.7|唯一字面数值—单位缺口→暂缓；同k margin控制原型|17适用/8患者，缺口4/3患者；软件反例揭示存在不等充分|[C可行性](C_feasibility.md)、[盲盘点](C_material_inventory.json)、c_materials091.py/selective091.py|一个窄观察量的具体实现与不开展临床比较的依据|已减少错误支持；构造/软件测试就是充分性gold；暂缓就是NA|

## 主表的直接核查范围

036本轮仅核对正式汇总与方法说明，不读取reserved逐例或原文；不重新开发或挑选方法。078从384条已有公开标签重新计算主文9个配置的混淆矩阵及指标，且逐例检查prior-only=PriorG。090对全部核心有效分数重放历史映射，与090冻结指标逐项相符，再按独立四正确性状态分解。085的177与180口径分别引用正式报告、对账和最终系统JSON，不运行任何R1代码或端点。

自检是执行者复算及来源检查，不替代独立审计；所有已有独立审计仍只按其原范围成立。论文主张没有用测试数量替代证据强度。

## 相关工作版本核对

VERI-DPO固定阅读[2026-07-03 v2正文](https://arxiv.org/html/2603.10494v2)，不是搜索引擎仍展示的旧题名摘要。§3.2说明单条HCNS噪声；§3.3/Eq.2说明偏好构造；§4.2—4.4及Tables5—8给出新版评估，§6限定评估人员、自动Judge和迁移范围。本稿只将其列为相关生成研究，不横比其NS率和本项目医生GT分类PA/MCC。

Sufficient Context核对[正文§3、§5](https://arxiv.org/html/2411.06037)；S2G-RAG核对[ACL2026官方页](https://aclanthology.org/2026.acl-long.1185/)；SURE-RAG核对[2026-07-24 v2](https://arxiv.org/abs/2605.03534v2)。三者不等于本项目运行过的基线。LLMLingua-2/RECOMP的原始技术目标已核对，Q90不冒充其实现。引用版本、章节与本文区别均进入稿件§2及参考文献，未把外部数字放入我们的成绩表。

## 主文与附录取舍

主文保留036、078、085、090的关键同ID表，084/087用紧凑叙述连接问题；079—083及086/088/089放附录脉络。原旧036稿和090局部草稿均原样保留，不覆盖或拼接其旧“当前状态”。不把036最终验证文字移到新配置上，不以论文收束为由删掉强标准校准对照、阴性或类别风险。
