> 阅读镜像：已省略44行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# 044：Incremental Evidence Recovery

## 核心结论

044完成了一个development-only、患者隔离的“保留原C48再增量补证据”实验。

结果不是一个可以宣布成功替换现有检索器的方法：

- 简单按rerank追加证据（rank）没有形成净收益；Score净正确−1，固定U2净正确−6。
- 学习型utility selector极其保守：696条evaluation中693条选择原C48不变，仅3条选择time增量包。
- 在687条三条件共同有效样本中，learned相对base在Score、U0、U2上均为 1 rescue / 0 harm，净+1，false-S均不增加。
- 这一改善仅发生在1名患者、1条claim，患者cluster bootstrap区间下界为0，因此不能据此声称稳定性能提升。
- 唯一被救回的claim同时通过了GT盲自动reason审计：新增证据后DeepSeek从错误NS变为正确S，reason也变为consistent、grounded、complete。

因此044最重要的结论是：

> “定向增量证据”机制再次得到一个真实正例，但当前可见特征训练出的utility模型正例信号过于稀疏，尚不足以形成可靠、可泛化的自动恢复器。

## 1. 实际冻结设计

本报告以收费调用前冻结的artifact为准，而不是以后被编辑过的工作区源码说明。

冻结设计使用的全部患者都属于已消费的development组，reserved overlap=0：

- utility训练：10名患者；
- 独立evaluation：8名不同患者；
- 两组患者完全隔离。

训练总体705条eligible claim中类别构成为：
- Supported 564；
- Not Supported 41；
- Not Addressed 100。

固定训练样本240条，使用类别加密配额：
- Supported 139；
- Not Supported 41；
- Not Addressed 60。

独立evaluation为696条eligible claim。另有24条固定repeat只用于运行稳定性诊断。

所有候选方案均保留原C48，不删除原证据；增量包最多约1500字符、最多2个passage。固定候选包为：
- rank：按原rerank优先追加；
- complement：强调相对已有C48的补充性；
- time：针对入院/出院/最终状态等时间语义调整候选顺序。

## 2. Utility监督与模型

训练阶段比较原C48与各增量包的原DeepSeek scoring verdict，并用医生GT定义下游utility：

- +1：原来错，追加后对；
- 0：正确性不变；
- −1：原来对，追加后错。

对于原始+1案例，另使用GT盲Qwen evidence/reason audit检查该“改对”是否伴随完整、grounded的解释；不满足者降为0。

434个有效训练pair中：

| utility | 原始Judge变化 | reason/evidence质量筛后 |
|---|---:|---:|
| +1 | 10 | 1 |
| 0 | 408 | 417 |
| −1 | 16 | 16 |

也就是说，真正可用于学习“安全增益”的正例只有1个。

最终本地模型为带标准化的L2 LogisticRegression，18个推理前可见特征，固定utility阈值0.02。模型部署时不读取GT、不读取Judge第一次回答，也不增加LLM调用环节。

训练患者leave-one-patient-out结果：
- 240条中238条选base；
- 1条选time；
- 1条选complement；
- Score净正确−1；
- U2净正确0。

训练阶段已经显示该模型倾向强烈abstain。

## 3. Evaluation执行完整性

冻结evaluation包含：
- 696条claim；
- base / rank / learned三种逻辑条件；
- 加24条三条件repeat；
- 共2160个逻辑输出；
- 因相同完整body共享请求，实际冻结1443个唯一DeepSeek请求。

原执行进程中断时留下8个“request已落盘但无receipt”的未知请求。为了避免可能的重复收费/重复回答，这8个没有重发。

其余264个从未发送的冻结请求后续安全恢复并完成。

最终唯一请求状态：
- valid：1432；
- valid_with_format_anomaly：2；
- invalid_core_fields：1；
- 无receipt未知：8。

三条件共同有效主分析为687/696。缺失不补标签，不使用available-case分别比较不同分母。

learned在全部696条上的冻结选择：
- base：693；
- time：3；
- rank/complement：0。

## 4. 主结果

| 条件 | 层 | 正确 | PA | MCC | false-S | S recall | NS recall | NA recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base | Score | 512 | 74.53% | .4309 | 15 | 81.08% | 61.40% | 36.00% |
| rank | Score | 511 | 74.38% | .4385 | 14 | 80.36% | 66.67% | 36.00% |
| learned | Score | 513 | 74.67% | .4324 | 15 | 81.26% | 61.40% | 36.00% |
| base | U2 | 562 | 81.80% | .4782 | 33 | 91.17% | 47.37% | 38.67% |
| rank | U2 | 556 | 80.93% | .4646 | 34 | 89.91% | 49.12% | 38.67% |
| learned | U2 | 563 | 81.95% | .4807 | 33 | 91.35% | 47.37% | 38.67% |

U0方向与Score类似：base 512正确，rank 513，learned 513。

## 5. 配对变化与作者异质性

learned vs base：
- Score：1 rescue / 0 harm，净+1；
- U0：1 / 0，净+1；
- U2：1 / 0，净+1；
- false-S变化：三层均0；
- 患者方向：1正、0负、7平。

Score PA差为+0.1456个百分点，患者bootstrap 95%区间约[0,+0.507]个百分点；Score MCC差+.0016，区间下界同样为0。效果过小，不能解释为稳定泛化优势。

rank vs base：
- Score：19 rescue / 20 harm，净−1；
- U0：20 / 19，净+1；
- U2：18 / 24，净−6。

更值得注意的是作者异质性。U2正确数：
- human：base 265 → rank 254，−11；
- LLM：base 297 → rank 302，+5。

因此“保留C48后统一再加一些高rerank证据”仍然存在明显作者代价，不适合作为默认部署策略。

learned没有修改任何human claim，所以human三层指标与base完全相同；3个增量选择全部发生在LLM claim中。

## 7. 稳定性与成本

24条固定repeat中：
- base Score标签变化1/24；
- rank Score 0/24；
- learned Score 1/24；
- base U2变化1/24；
- rank U2变化3/24；
- learned U2变化1/24。

因此本轮+1不能完全排除模型服务波动影响，但被救回案例的证据变化和reason变化具有明确内容对应，并不是“只看到标签变了就归因给检索”。

平均单次Judge prompt token：
- base：3069.5；
- rank：3488.9；
- learned：3070.9。

rank平均多约419 token；learned因为693/696不追加，平均只比base多约1.4 token。部署时三者仍然都是一次Judge调用。

收费API已用或保留：
- train score + train audit累计：¥10.641747；
- eval score已收到答案：¥18.768381；
- 8个未知请求费用预留：¥0.505215；
- changed-claim reason audit：¥0.078273；
- 合计：¥29.993616 / ¥80。

## 8. 如何解释044

044否定了两个过强预期。

第一，043的oracle证据效用不能靠简单“再加top rerank证据”稳定复现。rank条件虽然NS recall有所提高，但整体Score不增，U2还净损失6条，并出现human/LLM反向效应。

第二，当前18维本地utility特征还学不到足够可靠的正向恢复规律。根本限制不是分类器复杂度，而是监督信号：434个训练pair中只有1个通过reason/evidence质量门槛的真正正utility样本。

learned selector的优点是安全：
- 693/696选择不干预；
- 687条共同有效上0 harm；
- false-S不增加；
- 几乎不增加token成本。

但它的缺点同样明显：
- 实际只修好1条；
- 总体增益极小；
- 不能证明稳定泛化；
- U2-vs-Score结构冲突仍为83条，与base完全相同。

因此044没有解决整体reason-label不同步问题，也没有形成可宣布的新主方法。

## 9. 下一步研究含义

现在不应继续对Logistic阈值、18个特征权重或1500字符预算做事后搜索。

更合理的结论是：

> 高utility证据是稀有、关系型、往往与时间状态完成有关的事件；把每个append pack只压缩成静态数值特征，监督信号太稀疏。

如果继续该方向，下一步应优先解决“怎样获得更多可靠utility监督”，而不是先换更复杂分类器。可考虑：
- 在development中围绕原Judge明确写出的“缺失事实/关系”构造针对性候选，但训练阶段必须保持GT与推理输入隔离；
- 把计划→完成、早期→最终状态、数值/剂量变化等关系作为结构化候选类型，而不是通用相关性特征；
- 用pairwise preference学习区分“有用增量包 vs 相关但无用包”，并保留不干预选项；
- 仍然用患者隔离评价并同时报告标签与reason。

043仍然证明“真正目标证据有用”；044说明当前自动识别器还找不到足够多这样的证据。

## 10. 完整性与可复现性警告

冻结source inputs、model、eval choices、eval jobs与mapping哈希均保持不变，数值结果已从冻结jobs和真实receipt独立重建。

但当前工作区以下文件与model/planning freeze时保存的源码哈希不一致：
- tasks/044_incremental_evidence_recovery/common044.py
- tasks/044_incremental_evidence_recovery/prepare044.py
- tasks/044_incremental_evidence_recovery/protocol.md

因此当前状态为：

> executor recovery verification = PASS_WITH_PROVENANCE_WARNING

这意味着：
- 冻结模型、choices、API body、evaluation jobs和输入没有被事后改写；
- 本报告数值可以从冻结artifact和receipt重新计算；
- 但不能声称“从当前源码能够完整重建044的方法生成过程”。

在恢复上述freeze时版本源码前，源码级完整复现仍有缺口。

独立审计尚未执行。

## 11. 结果入口

- results_recovery_001/summary.json
- results_recovery_001/metrics.csv
- results_recovery_001/paired.csv
- results_recovery_001/repeats.csv
- eval_audit_recovery_001/summary.json
- verification_recovery_001.json
