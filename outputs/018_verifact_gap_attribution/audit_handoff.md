# 018独立审计交接

状态：执行者离线检查完成，**待独立审计**。没有自行宣布审计PASS，也未创建独立审计意见文件。当前代码、报告和机器结果以[handoff_001.json](handoff_001.json)的HEAD、工作区状态和SHA256为准；报告含新文件，不能只审Git HEAD。

## 建议核查范围

1. [report.md](report.md)是否把PA优势、S偏好和可实现headroom区分；重点核对010的`29=44−15`只为观察恒等式，不能当因果份额，016未补跑发布reference＋V4。
2. `preparation_001/ledger.jsonl`完整1251条，010实际答案来自010而非009；rater121绑定002原文件指纹。016主臂为首次V4，Q仅敏感性，未使用repeat/review挑结果。
3. `analysis_001`使用002 evaluate/paired_compare、每作者1000次患者bootstrap、missing=error。四格应为010=65/36/59/490，016=91/48/64/398；全量O/C正确1044/972，false-S79/27；两个队列四个作者分层均O PA高、MCC点估计低。
4. [诊断覆盖](diagnosis_001/summary.json)：78例/199字面锚点，54/240方向性全文深读，186未知，不得将`review_001`生成briefs冒称语义审完。两包完整内容按相同metadata/文本去重显示，`case_index.json`有复用依赖；O完整chain/final均在材料中。观察均为执行者判断，不是医学gold。
5. 重点双向病例：010 N180/N395/N526/N642及N139/N388/N248；016 S079/S092/S517/S575及S522/S281/S500。`trace_001/anchor_traces.json`区分候选前缺失、character_cap、max_per_note；不将不同位置笼统叫retrieval失败。短字面锚点可能有多处匹配，不将每个命中都判为关键证据。
6. 共同错/对保留24例，如S524/S601和S530/S550；共同正确不保证原理由正确，共同错误不等于缺证据。临床目标歧义和标签边界明确unknown，未改医生GT。
7. 001–017负结果及新患者边界保持，无收费请求、key读取、新优化或剩余患者正文读取。源数据文件哈希校验不等于读取保留患者病例正文。

## 复核入口

见[任务说明](../../tasks/018_verifact_gap_attribution/README.md)的三条命令。`verify018.py --output`指定不存在的新目录，在阻断网络下重新生成002统计、78例诊断、1251个pack与轨迹；`verification_001`已有95文件字节一致结果。18,121个非导航历史文件受保护。8项018完整性测试及15项002评价测试通过，原环境无pytest后使用unittest；过程见[execution_checks.json](execution_checks.json)。

重放证明机械复现，不自动证明语义归因正确；审计应自行核对关键全文和反证，按实际阅读范围给结论。当前没有原VeriFact上游候选日志，也没有passage-level医学标注；总体因果份额、最大可实现净headroom保持unknown。

审计期间停止改动同批正式成果。若需修订，追加修订记录和新交审快照，不覆盖本交接或历史001–017。
