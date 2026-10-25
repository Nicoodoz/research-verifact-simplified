# 087离线交审入口

本文件由执行者编写，**不是独立审计意见**。报告中的self-check只能说明执行者检查，不代替独立审核。

## 冻结与来源

- `freeze.json`记录首个087收费结果前的HEAD、协议/脚本/来源SHA、110 ID与440四臂请求；`sample_blind.jsonl`不含目标GT。
- `templates.json`、`template_changes.diff`、`reference_permutation.json`对应原F4、CL4删示例reference和X4固定3/4/1/2置换。目标claim/reference与接口保持不变。
- `coverage.json`区分22评价患者、PriorG来源16患者、实际四例4患者、071历史24人选例池；逐ID暴露与精确历史请求在sample文件。
- `budget.json`为20元原价预算与约5元缓冲。`attempts/*/request.json`和`receipt.json`追加保存；`attempt_ledger.jsonl`/`cost_ledger.json`为派生账本。

## 安全复查

不要运行历史086生成器来覆盖报告。日常只读用`run087.py status`；读取结果无需API。以下两条不联网、不重新拟合：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/087_f4_evidence_intervention/test087.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/087_f4_evidence_intervention/verify087.py --output outputs/087_f4_evidence_intervention/recheck_new.json
```

第二条必须给不存在的JSON路径，否则拒绝覆盖。它重读真实回执、重新解析、核对冻结输入/模型名/费用及完整预测；用sklearn交叉核对MCC、Macro-F1、混淆矩阵，重放公共配对患者bootstrap。`analyze087.py`是首次结果生成器，已有目标文件时会拒绝，不要删除工件来强行重跑。需要独立分析可从固定predictions逐条复算，原始回执与请求都有路径和SHA。

## 重点核查

1. 主机制结论使用共同核心有效原生raw；完整分母raw包含fallback已明确标识。系统主层为固定PriorG，U0/U2仅辅助。
2. F4−X4必须联合F4−B/X4−B解释；CL4区间跨零不能叫等效。所有固定比较均报告，探索区间未做多重校正。
3. 核心无效先分流，真实缺失raw/scores保持null；完整系统按逐ID冻结032 U2回退，绝不重试HTTP200内容。
4. `086_correction.md/json`及110条新归因台账仅为追加补正；原086 2救回/3伤害与所有冻结指标、自检、回执不变。
5. 作者原系统为同ID历史不同系统；历史B/F4只有确有精确请求的少量ID，不拼成110条同期成绩。
6. 费用按0731北京忙时输入3/输出9元每百万tokens计，包含失败/未知。实际token差不能由字符数相同代替；并发时长不证明端到端加速。

默认B及Frozen PriorG未改；未读取036/reserved工件，未修改.gitignore，085A/R1/AWS继续暂停。任务完成报告与自检后按用户授权提交推送，不自动启动088。
