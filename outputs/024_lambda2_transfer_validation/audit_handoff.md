# 024 独立审计交接

执行、正式评价及执行者自检完成；**待独立审计，执行者没有宣布审计PASS**。本次停止，不自动进入reserved40。

## 核心结论与分母

- DeepSeek U2−U0 +62/879、U2−B +37/878；Qwen +23/879、+21/879。
- 两模型同次S上的U2−U0 PA/MCC区间均正；相对普通B的MCC区间均跨0，均未达原强迁移证据门槛。
- 两模型新增false-S分别27/9。DeepSeek U2较历史020两轮少36/26条正确，不能继承历史绝对成绩。
- 1个DeepSeek B无效（verdict重复冲突），其S合法；不得把878分母的主描述表差值误当879的U2−U0。其ID为1e492144-2240-96c8-3ac4-ddd46dd22fca，request_id=511697dd941909be500dad6a。

## 必审材料

1. preparation_001/manifest.json、jobs.jsonl、cohort.csv：879冻结claim、同一API-BGE C48、同019prompt；body仅model更换。未新BGE、未reserved40。
2. protocol_001.md是原始协议；amendment_001是首次相同键无损修复；**amendment_002/README.md是用户后续明确授权且性能评价前登记的当前口径**。不能用旧“任意重复键停发/全合法才评价”判断本轮后续执行越权。
3. core024.py统一解析所有旧/新response，reason/checks异常只记diagnostic；不同值核心冲突invalid，HTTP200绝不重跑。原response、原严格解析状态和旧暂停均保留。27条valid_with_format_anomaly不是新增医生gold。
4. attempts全量3620次request/receipt：3516个HTTP200、104次通信未知；每个HTTP200唯一。未知预留6.658335不释放；usage峰时原价估算50.876109，总57.534444/80元。不是账单。
5. 曾出现代理路径断连；任务进程直连同一endpoint后续跑。未改OS代理、模型、prompt/证据；传输等价测试和源码指纹见amendment_002。network计数见verification_001/execution_diagnostics.json，不把时序改善说成严格网络因果证明。
6. analysis_001：每比较各自paired complete-case、完整/排除ID、n和hash；直接模型比较取共同有效集合。missing-as-error仅PA，不补三分类预测。002实现未改、1000患者cluster bootstrap、λ只0/2。
7. report.md为唯一主报告；CURRENT_STATUS、导航只同步现行状态。019–023报告/结果未改，旧024报告见status_history/paused_001和paused_002。

## 自检证据

- amendment_002/tests_before_evaluation.json：9个测试脚本共28项通过，含隔离临时目录的合成端到端评价；该合成数据不属于研究结果。
- verification_001/final_checks.json：3516 frozen body逐条重建、旧checkpoint/修订/请求回执hash、预算预留、3490条旧严格合法回答core不变；84项混淆矩阵/有效交集/净正确/false-S守恒核对。
- verification_001/replay.json：15份正式核心机器输出在outputs/replays/024_final_self_replay_001独立新目录重放，逐字节相同；该目录按已有.gitignore排除，可随时重建。没有改.gitignore。
- 正式分析manifest及最终交审manifest保留代码/输入/回执/成果指纹。HEAD和未提交状态在handoff.json；当前任务未提交/推送。

## 安全重放

```
python tasks/024_lambda2_transfer_validation/verify024_core.py
python tasks/024_lambda2_transfer_validation/check_results024.py
python tasks/024_lambda2_transfer_validation/analyze024_core.py --replay-dir outputs/replays/<new-directory>
```

禁止用run024*.py做离线复查；那些是真实收费入口。重放不覆盖历史目录。report中的paired_patient_changes.json为确定性派生补表，由report024_core.py生成，最终交审manifest另行绑定。

## 后续边界

此次只有跨服务/模型开发材料验证。Qwen不等于本地部署；分数不是校准医学概率；原解释不随U2改判重写；服务条件、非同期和单轮局限保持。是否冻结最终Judge并进入reserved40须独立审计后另行决定，本执行不启动后续工作。
