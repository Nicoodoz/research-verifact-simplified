# 028 独立审计交接

## 被交审结论

执行和执行者自检完成，**不宣称独立审计PASS**。停止当前语义核查路线，无新winner、不自动029或reserved40。

正式协议 `protocol_001.md`、输入 `preparation_001`、分析 `analysis_001`、图 `figures_001`、病例 `diagnosis_001`、人工观察 `semantic_001`。Git HEAD及未提交文件、SHA256见 `handoff_001.json`；环境见 `environment_001.json`。当前任务未提交、未推送。

## 优先复核项目

1. **发送前冻结与泄漏边界。** 025的103候选和026的52候选均纳入；底层879+650=1529条，16名已暴露development患者。冻结时间早于首请求。每个API user输入仅proposition/reference；没有GT、旧D/Q答案、作者、人工诊断或027错误类型。模型0731、C48、λ及历史输出未改。
2. **同期公平控制。** 原structured repeat与trace按GT盲hash交错，各155次，同模型、temperature0、thinking=false、max_tokens4096。repeat保持原200词解释要求，trace动态1–8项。非候选恒为原U0；两臂均只决定λ候选是否放行，拒绝时退回原U0，不用新NS/NA替换。SD来自历史025 OOF及026冻结迁移，非同期，需要保留该限制。
3. **唯一固定规则。** trace覆盖complete、所有关系supported、每项claim引用及全部证据引用按指定本地编号可定位才放行。只允许空白归一化。15条证据引用无法定位，涉及10例；4个真R仅因引用规则拒绝。没有事后修编号或宽松重评替换主结果。233项中90个回答仅1项，结构不保证细粒度或忠实关系判断。
4. **完整原始回执与费用。** 310请求均一次HTTP200、核心有效；无失败重试、无未知预留。原始body_text保留；解释/格式异常诊断不删除。费用按0731北京忙时输入3/输出9元每百万token估算3.798027元，非账单；发送前保守上界24.726546，累计上限80。依据为协议所链阿里云官方模型页。逐次usage和预留可复核。
5. **指标与严格参考。** 002实现计算PA/AC1/MCC/混淆矩阵，1000次患者cluster bootstrap；025、026、pooled及human/LLM分开。完整global-λ穷举至全S，未截λ范围；SD全概率阈值曲线另含原正式折内阈值工作点；repeat参考包含U0/repeat/U2和随机混合期望。混合包络是GT知情描述参考，不是可部署新方法。阈值未据结果重新选择。
6. **主要数字。** trace R/H/W=44/2/4，保留40%；SD=93/11/11，repeat=35/2/0。trace相对SD阻止19个旧错误支持、丢51个旧真救回、恢复2个旧漏救回、新增3个错误支持；三分类净−40。相对repeat净+9但区间跨0。在risk6处，相对SD/repeat/global混合包络分别−10.43/+2.02/+1.00R，区间均跨0。025负、026局部正，不能合并掩盖异质性。
7. **旧输入冲突。** 完整155为主；预存025六组37例与026七组22例另分析。合并候选二分类错误SD22、repeat29、trace30；新关系模式不同不等于risk–rescue改善。跨患者pair共享claim，不作为独立样本。
8. **病例与来源诊断。** 按事前两对旧冲突及转移分层hash选11例完整读；K01–K04与027旧packet的claim/C48逐字相同。保存11例原文锚点。额外4份只为历史发布reference，不是完整EHR；只作来源诊断，从未加入API。人工观察不是新医学gold；找不到证据仍unknown。

## 安全复核命令

使用已有research-verifact Python环境；以下命令只读历史，输出必须为不存在的新目录。不要运行 `prepare028.py` 或收费 `run028.py` 来复核。

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B tasks/028_traceable_claim_evidence_verification/replay028.py outputs/replays/audit028_replay_001
E:/miniconda3/envs/research-verifact/python.exe -B tasks/028_traceable_claim_evidence_verification/verify028.py outputs/028_traceable_claim_evidence_verification/audit_verification_001
E:/miniconda3/envs/research-verifact/python.exe -B -m unittest discover -s tasks/028_traceable_claim_evidence_verification -p test028.py -v
```

`replay028.py`阻断socket连接及DirectClient.send，从保存回执重建16个内容文件，要求与正式分析逐字节相同。不读密钥、不发API、不新拟合。

执行者已通过1672项核验和8项单元测试；Decimal独立算费用，独立逐标量检查引用放行、R/H/W及混淆矩阵；用线性规划独立检查全部matched工作点和所有留一患者混合包络。完整离线重放16/16一致，记录见 `verification_001`。这些检查属于执行者自检，审计者应独立判断协议、比较公平性及结论支持程度。

## 冻结与停止

交审后停止修改同批结果。只同步四份现行导航，不回写004–027报告、审计或历史指纹；未改.gitignore及API政策。核心负结论不依赖剩余预算或少量格式异常。后续不得以本任务授权继续换prompt、放宽规则、扩样或进入reserved40。
