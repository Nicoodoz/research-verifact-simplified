# 015审计阻塞修订入口

与014共用的R1/R2执行修订见[联合修订说明](../../014_qwen27b_baseline_comparison/revision_001/README.md)，等待独立定向复核。

015验证器只改变历史清单处理：明确的可变入口保留变化诊断；原014验证器通过旧快照/新版本双指纹登记；计算输入、代码、配置、回执和结果仍严格校验。原`verify015.py`字节保存在`original/tasks/015_disagreement_adjudication/verify015.py`，其他计算代码不改。Windows字节保护也已补齐。

原候选顺序偏差披露保持，仲裁523/650、最强单模型527、无候选542及费用¥2.0524446不变；没有新API或病例，无winner、不确认新患者、不做v2/v3。

验证依据为[015完整重放](../../014_qwen27b_baseline_comparison/revision_001/checks_002/replay015/verification.json)、[联合负向及Windows检出检查](../../014_qwen27b_baseline_comparison/revision_001/checks_002/checks.json)。196项断网测试通过、60个内容文件逐字节相同；精确修订交审版本见[handoff.json](handoff.json)。原独立审计意见保持不变，执行者不宣布PASS。
