# 015独立审计交接

2026-09-16（UTC+8）。执行与执行者断网自查完成，**无winner，停止方向，独立审计未开展**。唯一必读[中文主报告](report.md)。014仍待独立审计；本任务没有为014或015自行宣布PASS。

## 1. 被交审范围

固定014同六名既用开发患者650条valid claims（LLM243/human407）。基础预测取010 V4 C48 canonical与014 Qwen canonical；从完整原回执核对，复算的两模型完整指标对象与014一致。原claim和C48保持，78条分歧（LLM30/human48）各调用仲裁/无候选对照一次，572条一致原样接受。

仲裁器是V4的新调用上下文，不是第三个独立训练模型。只接收原claim、同C48及匿名候选完整判断；对照相同system/settings且仅省略候选字段。GT、author、source/BHC、隐藏病例、模型名称不进入请求body。候选顺序只由ID哈希决定，A为V4 44次、Qwen34次；没有候选交换、重复投票或挑答案。

[事前协议](protocol_001.md)、[授权](authority_001.json)、[准备manifest](preparation_001/manifest.json)、[理论上限](preparation_001/oracle.json)、[分歧清单](preparation_001/disagreements.csv)、`preparation_001/jobs.jsonl`和`candidate_sources.jsonl`给出精确输入与原回答对应。

候选顺序有一处协议文字偏差：文字写哈希首位，冻结代码实际整串整数取模2（等同末位），35/78条与首位写法的顺序不同。输入在调用前冻结、与GT无关，但不能称完全遵从该文字约定；详见[偏差记录](execution_deviation_001.md)。保留原数据，不重跑或推断另一顺序成绩。

## 2. 结果与停止

仲裁523/650、V4 526、Qwen527、无候选542。仲裁相对最强单模型−4，相对无候选−19；预设至少+20及其余多项条件失败，见[gate.json](analysis_001/gate.json)。无winner、不做v2/v3、不将对照事后换为winner。没有新患者确认，没有新增embedding/rerank/retrieval调用；只按既有002元数据预算过条件确认六名患者601条的数量，未读取其正文。reserved test保持隔离。

仲裁分歧32/78正确：保住V4独对13/35、救回Qwen独对19/36、均错0/7；没有使用第三标签。无候选51/78，但有目标替换或日期遗漏下的标签改对。不能把高标签分数或生成解释当语义金标准。两作者单独使用002 evaluate/paired_compare，完整分母、1000次患者cluster bootstrap，未做available-case或新增医学GT。

按事前作者×互补分组×仲裁对错规则选19例（不足格全取），完整核对原claim/reference和四份输出，保存50处字面引用。读取缓存仅复用逐字相同记录内容（包含元数据、换行），不做文本归一化后假称相同；N095首次工具显示截断后补读了其完整reference。选择样本不能估计总体机制比例。N216/N194候选reason字面复用、N448/N541引用编号沿用、N528/N193对照目标替换及N585日期遗漏均如实保留，不修改原有效标签。

## 3. 执行与费用

UTC 2026-09-15 16:00:49.740640至16:11:31.801478（UTC+8为9月16日）。156个HTTP200、156个有效答案，全部account_2，一次成功，无重试、余额切换、通信未知或失败预留。所有收费调用已停止。

- 仲裁78次：input294,231/output31,065/reasoning0 tokens；实际usage价格估算¥1.1152764。
- 无候选78次：input243,672/output27,821/reasoning0；估算¥0.9371682。
- 合计¥2.0524446，任务总上限¥40，非供应商账单；本次均非02–08点半价时段，差额来自实际usage缓存计数。
- 合法标签下解释/结构诊断仲裁14条、无候选15条，按原规则保留。无收费key测试，无重新收费生成基础650条。
- 部署成本另按共同无缓存/无时段优惠价格及历史实际usage重算：V4 ¥7.69494、Qwen ¥10.10856、双模型+仲裁¥18.965778/650条；1378次Judge调用。基础推理成本没有因旧答案复用而漏计；实验对照和历史失败不纳入理想部署，共有检索成本不重复计。

逐次原请求哈希、开始记录、完整原生回执、usage、费用及账号别名见`live/`与[尝试台账](analysis_001/attempts.csv)；价格核对来源见[sources_001.json](sources_001.json)。凭据不在成果内。

## 4. 自查和离线复核

[首次验证](verification_001/verification.json)记录：189项测试通过；11种请求/预测篡改负向检查；156个精确body及分歧成员核验；572条共同标签未变；两baseline完整指标对象与014一致；60个分析/案例/主报告内容逐字节重放；13,202个历史文件未变。新增候选顺序偏差披露后的最终验证为[verification_002](verification_002/verification.json)，首次报告快照仍在verification_001保留。验证阻断socket连接，新增API为0。自查不是独立审计。

Conda `research-verifact`，输出目录须不存在：

```powershell
python -B tasks/015_disagreement_adjudication/verify015.py --output outputs/015_disagreement_adjudication/verification_audit_001
```

不要重启收费`run015.py`、覆盖已有preparation/live/analysis/review/verification，或用新患者/新提示挽救结果。独立审计需要关注候选body与原输出绑定、GT隔离、完整评价、对照公平性、门槛是否原定、失败结果与成本表述。

## 5. 版本与历史保护

起始HEAD `de3da2f5af4045a4c814bc4279c4aab6a48c389d`；015尚未提交或推送。仅新增015任务/成果及测试，根README与AGENTS更新当前状态。原始数据、001–014成果、独立意见、`.gitignore`、`.gitattributes`和environment保持原字节。

准备manifest绑定调用前协议、授权、执行代码及旧回执；分析/阅读/解释是在结果后按事前范围生成。根状态文档是可变入口，不作为永久历史重放阻塞项。最终文件SHA-256、git状态、环境版本和自查绑定见[handoff.json](handoff.json)，其自身不纳入自身哈希。交审后停止修改同批成果，审计修订另留记录。
