# 014独立审计交接

状态：执行及执行者断网自查完成，**独立审计未开展**。所有收费调用已停止。唯一必读[中文主报告](report.md)；本文件为审计技术入口。

## 1. 范围与结论

用户交办固定009–010六名既用development患者的650条valid atomic claims（LLM243、人写407）；只调用Qwen3.8-27B，原claim、完整C48 reference、structured prompt、标签及生成设置不变。提前选定010已有完整V4 canonical结果为主对照，009旧C48为敏感性，不重新调用V4。没有剩余development、reserved test、检索/重排/prompt优化或本地部署实验。

Qwen的LLM/human ΔMCC为−0.011206/−0.025146，ΔPA为+0.004115/0；全部主差值患者bootstrap区间跨0。人写NA正确33→24，错误接受S 9→14。值得保留为较小模型研究候选，未证明非劣或可直接替换V4，不自动授权下一实验。

两模型运行非同期；请求仅换model不消除tokenizer、服务后端和生成波动差异。六患者已用于开发，不能称独立测试集。24例按事前规则选取并阅读完整reference与双方输出，69处字面引用已核验；重复块仅在全部内容及元数据逐字一致时引用此前完整阅读位置。案例观察不是新增医学GT、总体机制比例或内部因果证明。

## 2. 冻结材料与执行

- [事前协议](protocol_001.md)、[授权登记](authority_001.json)、[价格/接口来源](sources_001.json)。官方部署资料另存[来源补充](deployment_sources_002.json)，没有据此改变已运行设置。
- [准备manifest](preparation_001/manifest.json)：输入、650份历史V4对应回执、队列、原始命题文件及相关代码绑定；[原历史文件保护清单](preparation_001/history_sha256.json)。
- `preparation_001/jobs.jsonl`：650个不同完整请求body；与010逐条比较仅model字段不同。第一批4条是队列内canonical请求，兼容性通过后未改设置，无额外收费测试。
- `live/`：逐次调用开始记录、原生回执、usage、失败与累计预算。实际执行UTC 2026-09-15 13:50:52至15:27:03。650/650有效；660次HTTP尝试：650个200、9次通信未知、1个500，全部account_2。
- 收到回答的usage价格估算¥10.10856；9次通信未知保留¥0.5874；500未知usage保留¥0.065304。总占用¥10.761264，任务总上限¥40，非供应商账单。输入2,209,204/output290,079/reasoning0 tokens；按输入3元、输出12元/百万计价，不假设缓存优惠。
- 无答案失败按事前限制重试；成功HTTP回答不重生成、不挑答案、不补标签。Qwen64条格式/解释遵守诊断按原解析规则保留合法标签。
- 执行器、准备代码及协议在调用前冻结；分析、案例解释与报告在结果后生成并如实标记。没有改动历史run、原始数据、`.gitignore`或依赖。

## 3. 自查与复核入口

[verification_001/verification.json](verification_001/verification.json)记录：183项测试通过，10种输入/预测负向检查通过，650份请求仅换模型，010 V4完整指标对象重算一致，65个分析/案例/报告内容文件逐字节重放一致，12,374个历史文件未变。验证期间阻断socket连接，无API调用。该结果由执行者产生，不替代独立审计。

在Conda `research-verifact`中执行，输出目录须不存在：

```powershell
python -B tasks/014_qwen27b_baseline_comparison/verify014.py --output outputs/014_qwen27b_baseline_comparison/verification_audit_001
```

验证仅读取已有回执。不要重启`run014.py`或覆盖`preparation_001`、`live`、`analysis_001`、`review_001`与既有验证目录。所有统计使用002公共评价实现，非完整/重复/非法预测均报错。

## 4. 被交审版本

基于HEAD `b0312c2441bc386a418df91e4fc015f6ae18cdc3`；本任务尚未提交或推送。新增014任务/成果及测试，修改根README与AGENTS的当前状态。根文档为持续更新入口，未回写历史审计或run。

最终精确文件SHA-256、git状态、Python/依赖版本及验证绑定见[handoff.json](handoff.json)。该文件不包含自身哈希；对本任务文件与根状态文档作交审快照，既有依赖及历史文件以准备manifest和保护清单绑定。交审后不继续修改同批成果；后续审计修订另留版本，不自行写独立审计PASS。
