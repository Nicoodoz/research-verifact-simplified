# 089 交审入口

这是执行者自检交接，**独立审计未执行**。先读[中文报告](report.md)，再查[事前协议](../../tasks/089_source_audited_demo_compression/protocol.md)、[构造冻结](constructor_freeze.json)、[输入冻结](demonstration_freeze.json)、[样本/请求冻结](main_freeze.json)、[首个主回答前费用核对](preflight.json)。

重点可复核：

1. 原四例和目标C48未改身份/标签/顺序；模型及Frozen PriorG继承087；不读036/reserved，不恢复085A/R1/AWS。
2. 固定长槽P/Q各2次构造、2次独立检查。P失败不取消Q。两条P与一条Q格式失败的原始JSON、排序对象/漏ID/空候选要原样保留；不能写成全文医学必需或P有效压缩。
3. 本轮P4=F4完全同体，154个ID各共享1次；Q4有差异。逻辑462份对应308物理主请求，按logical_aliases映射，不能把共享零差当等效证据。
4. natural110每人5条、先盲冻结排序与规模；pressure44按NS/NA各22及患者轮转/每类每人最多3，不用历史对错。两面板无重复、结果分表，不合并自然PA。
5. source_units与source_changes.diff核验原文整段复制。source_risk_review和coverage_semantic_review区分出处成立与语义解释错误；核对不是新增医生GT，也不是压缩无损认证。
6. 原生raw、scores、core有效性独立保存。无效PriorG回退为同ID032 U2，raw缺scores不抹掉。归因先分fallback。所有救回/伤害与原VeriFact同ID历史参照均保存。
7. 公共evaluate/paired_compare，1000患者cluster bootstrap；完整/共同core/共同raw分别报；P-F、P-Q、Q-F全部固定呈现，无多比较校正、不把跨零当等效。
8. attempts保留全部请求/回执，原价含覆盖/构造/核对/主推理/未知/重试；总20元，构造合计2元；未优惠与共享物理账分开，未默认重发HTTP200。

离线复查：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/089_source_audited_demo_compression/test089.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/089_source_audited_demo_compression/verify089.py
```

再次verify仅核验，不覆写冻结结果，不联网。不要运行construct、coverage、prepare或api main作为复查。交付字节清单见delivery_manifest.json；stagecheck核对Git暂存blob与本地SHA，提交不包括密钥/原始数据/权重。源文和回执属于已有项目规则下的研究派生工件。

088保持“构造阶段未评价”，086更正只核实087已有文件存在。默认B/Frozen PriorG不升级；停止本版，不自动变比例、模型、示例或启动090。
