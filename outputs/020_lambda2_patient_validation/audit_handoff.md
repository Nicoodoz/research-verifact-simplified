# 020 独立审计交接

## 状态

- 任务：020_lambda2_patient_validation
- 执行日期：2026-09-18
- 当前状态：**执行与冻结分析完成，待独立审计**
- Git HEAD：9691b11bffe8fd0ea264a41a245e997ac12c91f6
- 未提交/未推送Git；.gitignore未修改。
- 本交接由执行者生成，不是独立审计PASS。

## 研究问题与冻结设计

019在旧650条开发材料上发现λ=2的总体PA/MCC网格信号，但未通过019原低false-S保护门槛。020不倒改019，而是预先固定λ=2，在003 development顺序最后10名患者的全部879条valid atomic claims上做两轮确认。

正式方法：
- C48构建沿009/016链路；
- 同一逐claim reference供B和评分prompt两轮使用；
- B为原structured prompt；
- U0为评分argmax；
- U2为同一评分输出上给Supported加固定λ=2后的离线标签；
- O为同ID VeriFact rater121 / R1-70B历史发布预测，仅离线对照；
- 主评价范围all micro，PA/MCC共同主指标，AC1与类别指标辅助；
- R0/R1分别评价，1000次患者cluster bootstrap。

## 数据与覆盖

- 患者：10名remaining development患者。
- valid atomic claims：879（LLM 269，human 610）。
- GT：S 630、NS 92、NA 157。
- Embedding：129/129收到。
- Rerank：879/879收到。
- Judge逻辑请求：3516/3516收到；发送尝试3523次。
- 40名reserved test未使用。
- 40名development现均已用于方法开发/确认。

## 主结果

| 轮次 | B PA/MCC | U0 PA/MCC | U2 PA/MCC | O PA/MCC |
|---:|---|---|---|---|
| R0 | 72.92% / 0.5268 | 73.95% / 0.5306 | **81.68% / 0.5960** | 76.68% / 0.5022 |
| R1 | 71.90% / 0.5080 | 71.67% / 0.5007 | **80.55% / 0.5711** | 76.68% / 0.5022 |

总体配对患者bootstrap：
- R0 U2−B：ΔPA +8.76 pp [ +6.30,+12.26 ]；ΔMCC +0.0692 [ +0.0257,+0.1226 ]。
- R1 U2−B：ΔPA +8.65 pp [ +4.71,+12.32 ]；ΔMCC +0.0631 [ +0.0049,+0.1114 ]。
- R0 U2−U0：ΔPA +7.74 pp；ΔMCC +0.0654；两区间均正。
- R1 U2−U0：ΔPA +8.87 pp；ΔMCC +0.0704；两区间均正。
- R0 U2−O：ΔPA +5.01 pp；ΔMCC +0.0938；两区间均正。
- R1 U2−O：ΔPA +3.87 pp；ΔMCC +0.0688；两区间均正。

## 必须审计的边界

1. false-S / NS权衡：U2 false-S R0/R1为47/52，B为17/16；NS正确U2为39/44，B为62/57。
2. LLM子组极不平衡：263/269为S；R0 U2相对B MCC下降，R1上升，不能宣称LLM MCC稳定获益。
3. human子组更稳定：PA两轮明显提高；MCC R0区间正、R1区间跨0；相对O两轮PA/MCC区间均正。
4. U2不会重写评分回答中的reason；分类性能与解释自洽性分开。
5. O是历史发布系统整体对照，不是同期同reference/同后端的纯因果对照。
6. 这10名患者未参与019阈值选择，但001/002做过全数据汇总，不称完全未接触独立测试。

## 稳定性与患者敏感性

- 两轮标签翻转：B 90、V_raw 100、U0 104、U2 81。
- 稳定救回73条；稳定伤害13条。
- U2−B逐患者：R0 10/10正向；R1 9/10正向、1名−5。
- U2−O逐患者：R0 9正/1负；R1 7正/1平/2负。
- 详见 analysis_001/patients.csv 与 leave_one_patient_out.csv。

## 执行异常与恢复

- Windows写live_ledger时发生文件占用；改为020本地双副本ledger与单调checkpoint，不改变请求。
- 1次硅基流动HTTP400/provider code20015 JSON decode error；冻结body本地JSON往返通过、大小普通。保留原失败回执及费用，以完全相同body重试后成功。
- 发送节奏使用前52份回答的usage-only统计做工程调整；未读GT/标签决定节奏。
- 最终3516份Judge回答均为siliconflow/account_2；没有明确额度耗尽或阿里云切换。
- 费用/未知预留44.28450852元 / 80元；不声称账单逐笔核验。

## 执行者验证

- 020专属离线测试：13/13 PASS。
- 全仓测试：223/223 PASS。
- receipt manifest：embedding 129、rerank 879、Judge 3523条哈希全部匹配。
- analysis manifest：18项全部匹配。
- 020启动前登记21,383个既有文件；收尾前除4个现行导航文档外均未变化。导航变化仅AGENTS.md、README.md、docs/API_POLICY.md、docs/PROJECT_STATUS.md；0历史文件缺失。
- verification_001.json记录上述检查；验证阶段新增API调用0。

## 权威成果入口

- protocol_001.md
- authority.json
- new10/preparation_002/
- new10/candidates_001/
- new10/base_preparation_001/
- new10_embedding/receipt_manifest.json
- new10_rerank/receipt_manifest.json
- new10_judge/receipt_manifest.json
- live_ledger.json
- analysis_001/
- report.md
- statistics.md
- verification_001.json
- execution_closure.json
- CURRENT.md

执行过程中误生成但未参与正式020的重复脚手架已移至 implementation_revisions/006_duplicate_scaffold_not_used/ 并明确标记non-authoritative。

## 核心文件 SHA-256

- report.md: 7949b4d28c235ffe5be8e44ee2d33511166dd457c11e13a0cf18e2fe78c81703
- statistics.md: 3d83e08c86fd86daef1aef6d9e146059fd4a38501bb8290af0d1ba5983c22467
- analysis_001/decision.json: f813af9e44bfc51b2ff94368d4487bcc735d1541daf4439ae156ec3f03e61f46
- analysis_001/metrics.json: 6b26e433c295d4407a9155ecfc18ab93872e873a2b7c7f157886cd4e71ff890d
- analysis_001/paired.json: 6ae1c59a523c928c34f5dafed83760632356fa7ba56763af9331522adc03336f
- new10_judge/receipt_manifest.json: e53017618e72e478b5b137aec883415d503ed350a733cb0e1d1e105dc7310bae

独立审计建议优先复核：λ=2冻结时间线、U2−U0离线决策实现、3516逻辑请求与3523回执绑定、费用台账、LLM子组解释边界及历史O对照定位。
