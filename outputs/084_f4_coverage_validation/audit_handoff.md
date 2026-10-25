# 084 独立审计交接

- 起始HEAD：`7ab688caaa5ced0941a8254e926c8b6780d893db`。任务开始时仅用户的084执行提示词未跟踪；本任务没有修改历史冻结成果、`.gitignore`或默认系统，没有commit/push。全部新增代码在`tasks/084_f4_coverage_validation/`，成果在本目录。执行者自检6043项PASS；**独立审计尚未执行**。
- 首个084收费调用与本轮评价GT连接前形成[协议](../../tasks/084_f4_coverage_validation/protocol.md)、`coverage_inventory.json`、`eligible_blind.jsonl`、`sample_blind.jsonl`、`main_jobs.jsonl`、`freeze.json`。`freeze.json`记录来源SHA、180条ID、360个请求体SHA与事前代价口径。032与历史532的1064个请求体逐一相同，见`historical_reference_consistency.json`。
- 原生尝试在`attempts/<attempt-hash>/request.json`及`receipt.json`，receipt绑定request SHA。`native_manifest.jsonl`逐条绑定同一次模型回答的verdict、分数、reason、checks、reasoning_content、usage和receipt SHA；`attempt_ledger.jsonl`包含所有360次尝试的原价费用、时长与来源。无重试、无HTTP0；360次HTTP200，3个内容核心无效按冻结U2回退。
- 083诊断只读原`oof_predictions.jsonl`、`fold_manifest.jsonl`、`models_frozen.json`，三者SHA见`083_oof_diagnosis.json`，没有新训练或改选。082历史532逐例从原`evaluation_predictions.jsonl`读取，24次重复从原`repeat_predictions.jsonl`读取，无历史工件改写。
- 首次评价之后发现071完整**训练患者池**与084有121条重叠；此前只检查了候选命题ID。更正与增加的描述性分层见[分析更正](analysis_amendment_001.md)。样本、请求、GT、主比较与代价门槛均未更改；59条池外不是新测试集。审计应分别检查071实际四例患者、24名训练候选患者、079校准患者和084评价患者，不把一个ID字段的0重叠误解为患者池隔离。
- 全仓库材料枚举初期，执行者曾只读查看036 reserved材料文件首条无标签记录的结构。这项不必要接触未用于构建候选池、抽样、调用、训练或评价；036医生GT与结果未读。正式来源SHA及请求绑定均不含036，应在独立审计中核实这一边界。
- 安全只读复核：`pwsh -File scripts/run_research.ps1 tasks/084_f4_coverage_validation/verify084.py`。该入口不读API密钥、不联网、不重训、不开新请求；只复算关键指标、来源哈希、同回答关联及费用。完整离线分析代码为`analyze084.py`，会重写本任务派生评价文件，需在副本中运行。**不要运行`run084.py`作为自检**，它是收费API执行器。
- 正式主口径为084新180条、完整分母、同ID B/F4＋Frozen PriorG；旧352、082新180、历史532和合并712各有独立表。配对PA/MCC采用统一`paired_compare`患者bootstrap1000次；错误支持率区间为同一21患者簇、固定预测的1000次重抽。执行者没有做084同体重复，082旧24次重复不作替代。
- 费用以阿里云`deepseek-v4-flash-0731`北京峰时未优惠输入¥3／输出¥9每百万token核算，实际¥12.166821／硬上限¥20；原价、预留和完成请求均可从attempt独立复算。历史缓存不抵扣部署完整流程成本。当前优惠、账单最终扣款可能不同，研究记账保守采用原价。

机器结果索引：[评价](evaluation_results.json) · [新增预测](new_predictions.jsonl) · [费用](cost_ledger.json) · [覆盖](coverage_inventory.csv) · [执行自检](selfcheck.json)。文件SHA清单由`handoff_manifest.json`保存。
