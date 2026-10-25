# 026 独立审计交接

2026-09-19。执行、正式评价、自检完成；**未开展或宣布独立审计PASS**。执行者结论：冻结SD未通过预设迁移门槛，停止当前版本。

## 审计对象

- [主报告](report.md)、[事前协议](protocol_001.md)、[当前状态](CURRENT_STATUS.md)。
- 基础HEAD：`a0a21eea46b2eec8e8478403e53b5b929291063a`。026尚未提交；当前代码／成果／导航改动清单及SHA256见`handoff_001.json`。历史024–025、原始数据和`.gitignore`未修改。
- 输入：019 selection/cohort.csv、preparation/inputs.jsonl；只复用6名development患者650条及其API-BGE C48，未读取reserved40病例。
- 训练：025 preparation_001/rows.jsonl里的024_D 103候选，10患者，与验证6患者不交叉。026未用历史019 score作主预测。
- 服务：登记及返回模型均为Ali `deepseek-v4-flash-0731` / `qwen3.8-27b`；temperature0、max_tokens2048、enable_thinking=false。现行API路由／政策保持。

## 优先核验

1. **冻结时序／训练隔离**：gate参数、scaler、阈值及feature代码在首个请求前锁定；阈值为原训练十患者内部LOPO确定的0.686248968514202。026 inference不fit，不使用验证GT或author/ID特征。
2. **条件Qwen调用**：D B650+S650完成后，只用新D score产生52候选；candidate manifest绑定全部1300个D回执，早于Qwen首请求。只有52个Q-S发送，650份Q模板不是650次调用。所有candidate有效，无缺失回退。
3. **核心解析及成本**：复用024务实解析器；1352个200全部核心有效，1323 valid、29 valid_with_format_anomaly；HTTP原始响应不改、无重复200。usage费用16.782714元，未知预留0，总保护80元。`cost_ledger.csv`与原请求的在途保护记录可逐条复核。
4. **比较公平性**：650条同分母；U0/U2/SD/peer来自同一次D评分。B也是650完整同期回答。Q只在candidate有输出，不能宣称Qwen全队列性能。
5. **full global frontier**：精确切换状态到全S，保持1e−6 floor和NS>NA>S tie规则。独立LP复核同风险随机混合包络；不要把单λ阶梯空档当成全部额外能力，也不要把事后GT构造的期望参考称为新已验证方法。
6. **患者敏感性**：沿002、1000次cluster bootstrap，权重为numeric（沿025已修正版frontier025_numeric），未在026bootstrap重训。SD混合增量2.1053、95%[−6.8947,11]，LOO仅4/6为正。去掉93640后确定性增量也为0。
7. **R/H/W解释**：SD相对U2阻止2H+4W、丢5R，因此false-S少6但正确数少3。LLM的所有候选放行，SD=U2；human才有筛选代价。不得把整体SD−B收益全部归功于gate。
8. **停止决定**：预先要求mixed增量≥3、LOO≥5/6未通过；不改门槛，不在peer较好后替换winner，不新增实验或reserved测试。

## 安全重放

在仓库根目录使用research-verifact环境。下述命令不调用模型；重放入口禁用socket及HTTP client的send，输出必须是新的`outputs/replays/`子目录：

```powershell
python -B tasks/026_frozen_sd_patient_transfer/replay026.py outputs/replays/audit026_replay_001
python -B tasks/026_frozen_sd_patient_transfer/verify026.py outputs/026_frozen_sd_patient_transfer/audit_verification_001
python -B -m unittest discover -s tasks/026_frozen_sd_patient_transfer -p "test*.py" -v
```

`verify026.py`是只读来源＋写新核查目录，不是独立审计意见生成器。它会重新拟合**旧024训练数据**以核对参数；这只是重建冻结训练，正式026推理及bootstrap不训练。已经存在的verification_001为执行者自检，不能覆盖。

执行者已运行禁网重放至`outputs/replays/026_self_replay_001`，15个分析文件逐字节一致。重放状态副本及哈希见交审快照；replays目录本来就不纳入Git。7项单元测试通过，此外LP独立数值核验、1352次预算／请求及1950份模板校验通过。自检数量不能当独立证据数量。

图表可在既有research环境（Matplotlib3.5.1）重建，不安装新依赖：

```powershell
python -B tasks/026_frozen_sd_patient_transfer/plot026.py outputs/replays/audit026_figures_001
```

图只有PNG/SVG，已视觉检查；机器曲线为权威数值。`supplement026.py`已经生成正式supplement_001，**不要直接重跑**覆盖原路径；附表可从已哈希的正式机器文件独立复算。

**不要运行prepare026.py、candidates026.py或run026.py来做审计。** 前两者是一次性冻结入口，后者是真实收费入口；请求已完成，无续跑需要。审计期间停止修改当前被审成果。

## 文件与限制

- gate_freeze和preparation_001 manifest记录API前代码与输入；candidate_freeze记录Q前白名单和D回执；analysis_001 manifest绑定使用回执及结果；handoff_001追加完整依赖／全部成果快照，不能替代API前冻结证据。
- 计算环境：supplement_001/environment.json；保留现有environment.yml，无环境变更。
- 原始request/response、score和解释可从attempts完整回查；最终标签改变时原reason不重写，不能把其当作最终标签的已核验解释。
- 新旧患者组不重叠，但019旧材料已暴露；只能称跨患者组迁移，不称全新测试。没有新医学gold、没有本地Qwen部署验证、没有临床安全保证。
- 本轮没有用户要求提交／推送GitHub，因此成果保留本地待审；无需以推送为理由启动任何调用。
