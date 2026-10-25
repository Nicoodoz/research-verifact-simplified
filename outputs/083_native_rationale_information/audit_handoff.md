# 083交审说明

执行者自检22,065项PASS，未做独立审计。零API、零重新拟合的安全入口必须给**全新**目录：

```powershell
pwsh -File scripts/run_research.ps1 tasks/083_native_rationale_information/verify083.py outputs/replays/083_verify_002
```

已执行[自检记录](selfcheck.json)复制自忽略目录`outputs/replays/083_verify_001/verification.json`。建议独立复核：

1. 2030份B/F4原生请求、回执、request/body/content SHA与082/079标签；不得把其它轮次理由拼进当前分数。
2. 083清洗仅纳入reason及三项证据／双方论据assessment；排除claim_summary和overall_assessment。每个非缺失结构论据须逐字引用清洗原文，不能视为新增医学GT。
3. 459条标签与1218条源比例均只来自14校准患者；14患者LOPO同时排除留出患者的词表、SVD、scaler、模型及源比例。模型/候选/患者列表在读评价GT前通过`evaluation_apply_freeze.json`绑定。
4. N/C/T/G/R同459训练ID、同权重、同数值基础；P和B迁移仅作辅助，029关系特征研究不能重命名为083首次贡献。
5. 完整532、旧352、新180、524核心有效、human/LLM、患者paired比较、错配531条、同分异GT与24条重复；尤其核对NS零预测和错误支持增量。
6. `cost_ledger.json`原价累计¥0.620007；每次发送前上界≤¥20、无重试/未知。原Judge历史成本单列，不计入083新增费用。

原始理由和引用包含临床内容，仅在受控仓库内审阅，不在公开报告复制。执行者PASS不等于独立审计。
