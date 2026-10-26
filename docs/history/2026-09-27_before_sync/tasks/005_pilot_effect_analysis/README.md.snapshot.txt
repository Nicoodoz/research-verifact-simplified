# 005：004 事件核对提示词的作用与退化分析

原主报告、交审清单、自查记录以及报告源稿中的“等待审计”保留形成时状态；以本入口和审计最新结论判断任务状态。后续研究优先级以[009入口](../../outputs/009_retrieval_baselines/README.md)为准，旧建议不是新的待执行授权。 tasks目录中的report.md/report_template.md及research_notes是本任务报告源稿或定向阅读底稿，不是滚动更新的项目状态页。

本任务为事后探索性分析，只使用 004 已有的 6 名开发患者、421 条有效 claims 和已保存回答，不调用模型、不补标签、不重新抽患者、不使用 reserved test。目标是解释 structured → event_alignment 的改善、退化及仍错变化，并选择下一步可验证、成本可控的研究问题；分析标签不是医生 GT，生成解释不是内部机制证据。

2026-09-14 中断前已读取当前正式报告和最新独立审计，计算了全量标签转移；没有生成 005 文件、逐例分析或遗留 Python 任务。恢复时 HEAD 为 `c4ff859b6e1ed991c3ce82ebaa7031c2729f9683`，已有多账号工具的未提交修改保留。本说明和选择算法在阅读本轮新病例正文前登记，但已知 004 总体结果，因此不是盲法或新的实验预注册。

全量分析覆盖全部 421 条的转移、GT 类别、患者、原医生一致性和输出格式诊断，指标继续使用 002 的 `evaluate` / `paired_compare`，完整队列、1,000 次患者 bootstrap。辅助计数仅作描述，不将选例比例推为总体机制比例。

深入选例：每种作者的改善/退化各 4 例，优先覆盖不同 GT→两臂标签组合，再覆盖不同患者，余下按固定 SHA-256 排序。纳入全部 3 条两臂标签不同但均错误的 human 命题；每种作者再选稳定正确 S、稳定正确非 S、稳定错误 S 各 1 例，优先补齐患者覆盖。共 25 例；不按正文是否支持假设挑选。全部 58 条标签变化及 6 个对照另保留完整输出供回查；实际阅读范围逐例记录。

深入病例均核对原命题、完整 reference 和两臂完整输出。相同患者不同 reference 的逐字相同事实块可合并阅读，但保留每个原 reference 的完整文本、顺序、编号和对应关系。观察、解释假设、未解决处分别记录，并用原文字符位置校验引用。若需补读其他病例或 EHR，另记理由与范围，不替换原选例。

执行：`python -B tasks/005_pilot_effect_analysis/effect_analysis.py extract`。每次提取新建 `outputs/005_pilot_effect_analysis/run_XXX`；不会覆盖旧 run。后续解释与正式报告入口见输出 README。初次提取脚本名为 analyze.py，后为避免与 003 同名模块冲突改为 effect_analysis.py；算法和选例不因改名变化。

## 完成与复现

已通过2026-09-14独立审计，无阻塞修正；依据见[审计记录](../../reviews/005_pilot_effect_analysis.md)。正式入口为 [run_002/review_002/report.md](../../outputs/005_pilot_effect_analysis/run_002/review_002/report.md)。原始回执重放验证完整 181/240 配对，指标与 004 一致；没有新增临床判断标签。25 例共阅读 50 份完整生成输出；完整 reference 通过 1,283 个去重事实块及其逐病例编号对应阅读，块尾分隔空白只在阅读并集中去除，原始 reference 全文不改。其余 39 个 X_ 包只保存，没有精读声明。

补读原文上下文在完整 reference 阅读之后另行登记：[context_request.json](../../outputs/005_pilot_effect_analysis/run_002/context_request.json) 指定 13 例。`context.py` 只按这些 proposition_id 从官方 propositions 文件提取 parent/BHC，并检查源文件哈希；实际阅读为 13 个 parent 和 C17 的完整 BHC，不将来源文本当 EHR 证据。

`review_notes.json` 是执行者阅读后形成的解释记录，不能自动重新产生医学判断；`report_template.md` 是简明主报告源稿。`build_effect_review.py` 校验提取材料与引用，保留完整输入输出，生成新的 review 目录。复现命令（使用 Conda research-verifact）：

```powershell
python -B tasks/005_pilot_effect_analysis/build_effect_review.py --run outputs/005_pilot_effect_analysis/run_002
python -B tasks/005_pilot_effect_analysis/verify_effect_analysis.py
```

自查命令禁用 Python 网络连接后运行全项目测试、重复提取/渲染，核对 004 指标、原始来源上下文、全部 reference 覆盖及证据/输出锚点，每次新建 verification 目录。005完成时104项测试通过，86 个提取文件及 30 个最终报告文件重复一致，见 [verification_001](../../outputs/005_pilot_effect_analysis/verification_001/verification.json)。005 脚本采用独立模块名，避免与 003 的 analyze/build_review 同名模块冲突。

005当时建议先验证“局部来源上下文用于确定核验对象/范围、EHR 单独提供证据”，其收益与论文贡献未确立。该候选已由006检验，仍未证明净收益；以后交办任务需登记实际队列与预算，费用确认遵循 [当前 API 费用规则](../../AGENTS.md#api-调用费用与确认规则)：任务预估总费用不超过 40 元可直接执行，超过则先确认。研究建议不把 004 的阴性/不一致结果解释成事件方向整体无效。
