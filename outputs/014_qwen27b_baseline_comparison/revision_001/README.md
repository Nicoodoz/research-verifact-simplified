# 014/015共用复现阻塞修订

针对[014审计R1/R2](../../../reviews/014_qwen27b_baseline_comparison.md)与[015审计](../../../reviews/015_disagreement_adjudication.md)的执行修订已完成并通过自查，等待独立定向复核。原研究结论保持：014可保留Qwen研究候选但未证明非劣；015无winner并停止。没有新增API、样本或研究实验。

## 修改内容

- **R1：可变入口与计算材料分开。** 新增`replay_history.py`，只把明确列出的根入口、各任务顶层README、顶层独立审计意见及审计索引、账号说明、`.gitattributes`作为状态快照，逐项报告历史/当前指纹及变化。嵌套历史README、审计证据目录、主报告、协议、输入、回执、配置、指标和计算代码仍严格检查。原`check_hashes`及prepare/analysis中的严格绑定未修改，状态策略仅用于历史保护清单，不覆盖计算依赖的严格校验。
- **014验证器的显式版本绑定。** 原`verify014.py`保存在`original/tasks/014_qwen27b_baseline_comparison/verify014.py`，与015旧历史清单中的原SHA一致。新`replay_bindings.json`同时绑定原快照和当前修订验证器；只允许这个明确路径作为旧自查来源更新，不能据此放开其他014源码。015原验证器另保存在015 revision_001中。
- **R2：Windows字节保护。** `.gitattributes`新增014/015任务、对应测试及审计文件的`-text`，并为真实检出发现的11个共享冻结计算文件补同样属性。没有修改这些计算文件的字节、全局Git配置或`.gitignore`。

调用前manifest、历史保护清单、原回执、预测、指标、费用、两份正式主报告及原handoff均保留。审计原意见和审计证据不由执行者修改。

## 验证材料

- [checks_002/checks.json](checks_002/checks.json)：两项完整重放同时模拟正常审计/入口/属性文字更新；各自运行全部断网测试，并保持014的65个、015的60个内容文件与正式结果逐字节一致。
- [Windows隔离检出](checks_002/checkout.json)：独立Git index使用HEAD加本次源码/属性修改，`core.autocrlf=true`真实checkout-index检出；39个任务源码、测试和全部直接冻结计算依赖逐字节相同。没有修改用户工作区index或Git配置。
- 12项隔离篡改：014/015分别改变冻结请求、回执、计算代码、授权/配置、指标、主报告，正常验证入口必须拒绝。磁盘原成果未作临时篡改；仅将读取层路由到改变后的隔离字节。
- 新增7项回归测试覆盖状态变化可见、嵌套历史/审计证据继续严格、原验证器快照和当前绑定、计算代码不能任意登记替代，以及公共manifest检查仍严格。
- [checks_001/checkout.json](checks_001/checkout.json)保留第一次检出失败：它暴露了11个共享依赖也需要字节保护，补属性后进行checks_002。失败记录未删除，不把首次失败称通过。
- [before.json](before.json)是修改前13,599个已有文件的指纹；[保持检查](preservation.json)确认仅9个授权修订文件发生变化，其余13,590个已有文件逐字节不变，包含独立审计意见/证据、原报告、指标与回执。精确交审版本见[handoff.json](handoff.json)。

最终两任务各196项测试通过；014严格历史项12,332、可变状态项42，015严格历史项13,157、可变状态项44、显式旧验证器修订1，分别完整覆盖原12,374/13,202项清单，不删除原清单或改写历史哈希。

重放修订检查（新输出目录必须不存在，全部断网）：

```powershell
python -B tasks/014_qwen27b_baseline_comparison/check_revision014015.py --output outputs/014_qwen27b_baseline_comparison/revision_001/checks_audit_001
```

日常014/015原`verify014.py`/`verify015.py --output <新目录>`继续可用。历史总项数仍记录；`history_files_unchanged`现仅表示严格未变项，可变状态和已绑定旧验证器另列于`history_validation`，不再把它们误称原字节未变。

上述为执行者修订自查，不代表独立审计PASS；不自动提交推送。
