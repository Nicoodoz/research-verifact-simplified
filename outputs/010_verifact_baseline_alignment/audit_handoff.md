# 010独立审计交接

**执行完成，等待独立审计。** 先读[唯一主报告](report.md)。本文件由执行者写，未代写独立PASS，未修改任何历史审计原文。全部模型调用结束，交审后停止修改同批成果。

## 实际被审版本

- 开始时本地`main`干净；HEAD及fetch后的`origin/main`均为`b336a6fd01755e2e6cbf1da55656826e43b51182`。
- 010尚未提交。当前被审版本为该HEAD加[handoff_001.json](handoff_001.json)列出的未提交字节：新增`tasks/010_verifact_baseline_alignment/`、`outputs/010_verifact_baseline_alignment/`和`tests/test_baseline_alignment.py`，修改根`README.md`与`AGENTS.md`。
- 版本清单包含实际代码、配置、输入、所有回执、分析、案例、验证材料及当前入口；清单自身不自哈希。独立审计开始时应先验证清单，若存在未登记变化，先区分并发修改与后续独立审计材料，不审一个仍在变化的版本。
- 009的3317个历史文件已在运行前取哈希，运行后全部一致；对照入口`readiness_001/009_before_hashes.json`。没有修改009代码、历史run、原始EHR、原医生标签、既有答案、`.gitignore`或环境依赖。

## 建议复核顺序

1. **原始对应与两层口径。** `preparation_001/release_binding.json`、`cohort.csv`、`inputs.jsonl`、`released_predictions.csv`：是否恰好650个009 valid claim，唯一rater-121及其实际reference、模型与哈希；原预测与002交叉检查。发布系统分数只作same-cohort system reference。
2. **同期请求与运行完整性。** `execution_protocol_001.md`、`authority_001.json`、`preparation_001/jobs.jsonl`/`assignments.csv`/`repeats.json`和`live/judge`：两臂是否只有reference字段不同，C48 body是否与009相同；原claim不变、没有来源自证；1300主请求和24预登记重复，没有挑答案或补标签。1324有效/1329HTTP，4个402及1个未知结果保存。
3. **评分与成本。** `analysis_001`、`tables_001`、`additional_diagnostics_001`：650完整配对，作者/类别/患者/区间一致；旧C48变化与同输入重复不算reference增益。usage估算¥23.3620932＋未知请求保留¥0.105018=¥23.4671112＜40，含重复/重试，非账单。
4. **证据诊断是否越界。** 全量结构、metadata匹配、多重匹配/未匹配保留；274显示逆序/302对能与完整CHARTTIME相容，不说原排序bug。34例正式解释为`review_002/semantic_001`，75处引用；初选26例及补全8条NS有记录。N180、N642、N430、N585的真实信息增加，以及N394/N420/N248反例；N071、N095、N310的标签/语境分离，N103重复翻转均需保留。
5. **结论边界。** 比较两套完整实际reference，长度/内容/格式共同变化，不是等预算单变量包装消融。C48实用可用不等于最优或非劣；010没有实施新packaging、修Judge或优化检索。基础metadata/断句修正不能自动作为论文创新。

## 已完成的执行自查与复核命令

`verification_001/verification.json`：150项断网测试通过，原release映射、完整请求/回执、72803个reference块及原文偏移核对；评分、案例渲染和补充诊断逐字节重放。`final_checks_001`补查当前文档链接、编码、冻结材料以及隔离的输入/代码/结果变动拒绝，正常状态和审计文档不阻断。

在`research-verifact` Conda环境、仓库根目录运行，只写一个新的010验证目录：

```powershell
python -B tasks/010_verifact_baseline_alignment/verify_alignment.py --output outputs/010_verifact_baseline_alignment/verification_audit_001
```

命令本身阻断网络，不能触发API。无需重跑`prepare_alignment.py`或`register010.py`，不要运行live执行器。所有已存在验证目录保留；再次执行选择新目录。根README/AGENTS/审计变化仅记录诊断，冻结计算材料继续校验。版本清单是本次交审快照，不要求以后正常状态追加一直匹配该快照。

已知限制和收尾：无新医生gold；仅六名既有开发患者、LLM NS/NA=10/5；reference内容和预算未单独控制；服务只给模型别名，温度0仍有跨运行/重复变化；费用非账单。没有剩余收费工作，**停止扩展，交独立Codex审计**。
