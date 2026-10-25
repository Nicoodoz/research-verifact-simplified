# 081 交审说明

执行起点HEAD：`557f859dd33a5898763b377263d2b1044d4cedb5`。研究结项时未自动commit/push；随后用户另行授权推送。任务开始即存在用户工作区改动`D test_bedrock.py`，未触碰。新增代码在`tasks/081_gt_blind_evidence_selection/`，新增结果仅在`outputs/081_gt_blind_evidence_selection/`，现行状态仅更新根README、AGENTS与`docs/PROJECT_STATUS.md`；未修改`.gitignore`、原始数据、066–080冻结工件、PriorG、Judge或reserved。

建议审计顺序：

1. 核对[协议](../../tasks/081_gt_blind_evidence_selection/protocol.md)、`sample_freeze.json`、`stage1_cost_estimate.json`与首个attempt时间；确认96个U包的`u_packs_freeze.json`早于`gt_join_freeze.json`。
2. 对照`u_plan_jobs.jsonl`、`u_compose_jobs.jsonl`与T对应请求，检查唯一额外GT字段、同C48候选、同formatter；检查`judge_jobs.jsonl`仅含claim和reference，按哈希交错。
3. 从`attempts/*/{request,receipt}.json`重算816个成功回答及1个HTTP0预留；全任务账本为`cost_ledger_final.json`，无成功同体重发，重复阶段仅重发48条×3臂固定诊断。
4. 使用`case_results.jsonl`、`repeat_case_results.jsonl`调用公共`evaluate`/`paired_compare`重算主表及重复表；保留5个首轮核心无效和2个重复轮核心无效的预设U2回退。
5. 复查抽样暴露缺口：066–069诊断ID未事先加入排除优先级，47条重叠，其中067有41条。`overlap_sensitivity.json`为后验描述，不改主队列。

执行者自检命令：`pwsh -File scripts/run_research.ps1 tasks/081_gt_blind_evidence_selection/verify081.py`。本次1299项PASS，[自检指纹](self_check.json)记录样本与机器结果SHA256；**不等于独立审计**。原始机密EHR与密钥不应在外部报告或提交中暴露。

相关回归测试：`research-verifact-029`中的`test_retrieval_planning.py` 9项PASS；`test_evaluation.py`在该环境因未安装`irrCAC`无法收集，改在原`research-verifact`环境运行15项PASS。共同评价代码已经被081主分析与重复分析实际调用；未修改评价实现。
