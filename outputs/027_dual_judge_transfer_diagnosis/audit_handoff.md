# 027 独立审计交接

执行、自检、报告完成；**独立审计待开展**。无新API、无拟合、无新winner，无reserved病例访问。

## 被审范围与优先问题

基础HEAD：`57ca6fc45d8d9f3f051579b9e46240065b59082e`。当前027未提交；最终文件／代码／来源／导航指纹、dirty清单见handoff_001.json。历史025/026审计PASS保持，不由执行者改写独立意见。

1. **概率来源**：025患者OOF来自analysis_003/candidate_oof.csv；026正式计算逐值读取已保存gate_inference.json。只重算同一冻结参数作一致性检查，无fit。原十患者上的final_gate_probability仅训练内描述；不得把其0.820 AUC当泛化证据。
2. **公平参考**：保留全879／650条各自全部非负global状态到全S，未缩到candidate或λ≤2。局部比较则严格只在同一λ2候选内，其他claim保持U0。025正式折内阈值R64/risk10与统一OOF概率曲线不同，不可互相冒充。
3. **阈值诊断**：≥80%区域扫全distinct概率，ties统一。026最大完整包络额外rescue2.368、无点≥3；此上限是事后曲线诊断，不输出新工作点。原固定threshold=0.686248968514202未改。
4. **不确定性**：所有1000次重抽以完整队列患者为cluster（026含无candidate的第六人），固定输出、不重训；单类抽样AUC不可算则登记。高rescue风险摘要要报告实际R，不能把tie导致的不同R当严格同rescue。池化OOF分数跨折可比性有限。
5. **冲突组**：使用精确12维向量，不四舍五入；6原score近似差≤5/10仅作成对描述，不传递聚类。GT理想参考要求整组放行／拒绝。观察到的数学限制不代表总体Bayes上限，不把近邻距离当不可分证明。
6. **病例**：完整17错误＋6拒绝风险对照＋8分层哈希保留R，31例53引文偏移。观察、假说、unknown与原GT分开。C06/C16、C14/C29完全同输入但GT不同是重点；C17–19同患者句型，不能算独立重复机制。Q-S100是单边而非双边高支持。
7. **停止结论**：现有输入有信息，但当前无充分依据仅改阈值／融合救结果；对新信息的建议是条件性的，不自动开展实验。不能把任一事后阈值或peer当新winner。

## 正式版本与工程记录

- analysis_001保留首次用冻结JSON参数复算的等价概率；analysis_002改为逐值读取026已保存概率。差别仅浮点末位，不修改Gate、特征、训练、标签或case集合。两版代码分别保留，原manifest继续可验。
- 正式图figures_002；首稿figures_001高rescue风险图阶梯方向已在正式版改为`pre`并去除同R冗余risk状态。原图保留，报告只引用正式图。数据和结论未因绘图改变。
- reading_view生成脚本第一次遇Python3.11 f-string反斜杠语法错误，在任何该视图产物生成前改为预先压缩字符串；无数据、模型或统计变化。完整case_material已保存，视图仅去重文本块和压缩空白。

## 安全复查

仓库根目录research-verifact环境；以下输出目录必须不存在：

```powershell
python -B tasks/027_dual_judge_transfer_diagnosis/replay027.py outputs/replays/audit027_replay_001
python -B tasks/027_dual_judge_transfer_diagnosis/verify027.py outputs/027_dual_judge_transfer_diagnosis/audit_verification_001
python -B -m unittest discover -s tasks/027_dual_judge_transfer_diagnosis -p "test*.py" -v
```

入口拦截socket连接以及LogisticRegression.fit／StandardScaler.fit，不读取密钥、不调用client。verify只核验并写新目录；不是独立审计意见生成器。**不要重跑cases027.py、semantic027.py、interpret027.py、finish027.py到正式目录**，它们一次性产物已冻结。图可用research环境（Matplotlib3.5.1）：

```powershell
python -B tasks/027_dual_judge_transfer_diagnosis/plot027.py outputs/replays/audit027_figures_001
```

执行者已自检：6项单元测试通过；685项来源/数值/引文检查通过。直接成对计算AUROC；所有曲线用002与RHW逐点重算；完整global逐点匹配已审025/026；LP核验混合边界、MILP独立核验GT组级参考。禁网重放11份正式内容文件逐字节相同，源位置outputs/replays/027_self_replay_001，摘要复制至verification_001。图已实际查看。

独立审计可优先重复数值检查并抽查原回执／case锚点；本次没有重审全部1352个026 HTTP回执，而是沿用已审且哈希匹配的normalized来源。特征输入、原回执、GT和旧报告未改，不能将执行者语义观察当新gold。环境版本记录见environment_001.json。

## 停止与交接

研究结论以report.md为唯一主报告。冻结λ=2、最终Gate及026停线结论保持；不新增费用，不进入reserved40，不自动下一任务。当前用户没有要求提交／推送027，成果留本地待审。交审快照形成后停止修改同批成果。
