# 082交审说明

本任务由执行者完成零API自检，未作独立审计。可从全新目录运行：

082执行结项时本地HEAD与GitHub `origin/HEAD`一致，均为`e2d2b8c021d81f01b5a2cd512e2fff89ad35e94b`；082为新目录，用户原有`test_bedrock.py`删除状态保持原样。研究执行时未自动提交或推送；此后用户另行授权推送082成果。

```powershell
pwsh -File scripts/run_research.ps1 tasks/082_anchor_configuration_adaptation/verify082.py outputs/replays/082_verify_002
```

该入口不发送API、不覆盖正式结果。已运行的[自检记录](selfcheck.json)为3750项PASS，原始运行文件位于忽略目录`outputs/replays/082_verify_001/verification.json`。优先独立复核：

1. `blind_freeze.json`、`training_effective.json`、`evaluation_apply_freeze.json`的先后、SHA绑定和14/22患者隔离；完整教学候选池重叠须按敏感性解释。
2. 420筛选GT、旧114、历史1378标签的集合去重；不能把配对B/F4分数算两份新标签。
3. `model082.py`的同视图I/S/A损失、权重、参数数目／正尺度、LOPO折内参考先验；三族训练gate均不满足。
4. `evaluation_predictions.jsonl`与公开`evaluate/paired_compare`、旧352历史逐例标签、无效回退及新180选样历史曝光。
5. `attempts/`、缓存精确请求体和`cost_ledger.json`；¥50上限按忙时未优惠价，优惠估计只附列。
6. 未加权敏感性补充更正：`unweighted_models_frozen.json`首次记录保留，正式`unweighted_models_frozen_v2.json`在读取评价GT前绑定；主源码SHA恢复与主模型冻结一致，详见[更正记录](unweighted_sensitivity_amendment_before_evaluation_GT.md)。

原始回执含临床输入，仅在受控仓库内核查，不在公开报告复制原文。执行者自检通过不代表独立审计通过。
