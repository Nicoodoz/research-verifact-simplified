# 项目现状总览

**020执行与冻结分析完成（2026-09-18，尚未独立审计）。** 固定019网格中事后候选λ=2，在003开发顺序最后10名患者879条valid atomic claims上完成B/评分版各两轮。总体U2相对同期B：R0 PA 81.68% vs 72.92%、MCC 0.5960 vs 0.5268；R1 PA 80.55% vs 71.90%、MCC 0.5711 vs 0.5080；两轮PA/MCC患者bootstrap差值区间均为正。U2相对U0及同ID原VeriFact O的总体PA/MCC两轮差值区间也均为正。false-S较B增加、NS识别下降，LLM子组MCC跨轮不稳定；020不是最终reserved-test结论。累计44.28450852元/80元，3516份Judge均来自硅基流动account_2，未切平台；40名reserved test未使用。[020主报告](../outputs/020_lambda2_patient_validation/report.md)。

本会话最新API路由优先：先硅基流动启用key池，只有全池真实明确额度耗尽后才转阿里云单key；保留成功回答和未知费用，跨阶段/账号/平台累计80元。此前其他路由描述按历史版本理解。

以下旧状态按形成时理解；当前状态以本页020段、020主报告及最新独立审计为准。019原低false-S门槛失败结论保留，不因020采用总体PA/MCC确认目标而倒改。

更新：2026-09-18。当前状态入口；历史版本中的“待审／暂停／下一步”不覆盖本页与最新独立审计。

## 当前结论

**020当前：** 固定λ=2在剩余10名development患者879条valid atomic claims上完成双轮确认。总体U2相对同期B、U0和同ID原VeriFact O的PA/MCC两轮均提高，患者bootstrap差值区间下界均为正；human信号较稳定，LLM因263/269为S且MCC跨轮不一致需谨慎解释。false-S较B增加且NS正确数下降。020已完成执行/分析与收尾自查，尚未独立审计；40名reserved test未使用，不能自动开启最终测试。[020主报告](../outputs/020_lambda2_patient_validation/report.md) · [统计附录](../outputs/020_lambda2_patient_validation/statistics.md) · [交审材料](../outputs/020_lambda2_patient_validation/audit_handoff.md)。

**019历史结果：** 固定证据支持边界筛查的原低false-S保护门槛未通过；λ=2在旧650条开发材料上出现总体PA/MCC开发信号，随后由020按新研究目标固定后确认。019结论不倒改，尚未独立审计。[019主报告](../outputs/019_support_boundary_screen/report.md)。

**018当前：** 018完成010/016两批12名已暴露患者1251条离线差距诊断：原VeriFact独对156、C48＋V4独对84，净差+72主要来自S召回，同时false-S为79/27且原系统MCC点估计更低。010固定V4后发布reference净−15，不支持将发布系统PA优势主要归于reference。优先研究Judge支持边界；真实可优化净headroom仍unknown。78例深读，186条方向性机制未充分深读，保留unknown；0新增API，无新优化或新患者实验。快速独立审计PASS，可冻结／结项，见[018审计](../reviews/018_verifact_gap_attribution.md)。见[中文主报告](../outputs/018_verifact_gap_attribution/report.md)与[交审材料](../outputs/018_verifact_gap_attribution/audit_handoff.md)。

**017历史结果：** 017完成12名已暴露患者192条GT盲证据干预：19条稳定错误中稳定救回0条，160条稳定正确中破坏3条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。快速独立审计PASS，可冻结／结项，见[017审计](../reviews/017_verification_supervised_evidence_utility.md)；[唯一中文主报告](../outputs/017_verification_supervised_evidence_utility/report.md)与[交审入口](../outputs/017_verification_supervised_evidence_utility/audit_handoff.md)。

001–018已完成并有相应独立审计依据；019与020已完成执行/分析但尚未独立审计。020把固定λ=2提升为development层面的新患者双轮验证信号，但不是最终测试结论，也不自动启动reserved test或替换core。

| 研究阶段 | 已形成的结论与边界 |
|---|---|
| 001–003 | 数据审计、002统一评价和003冻结患者分组保留；任务完成不代表原始标签／数据异常全部消失 |
| 004–009 | 多轮方法实验及负结果保留；009 C48是当前实用证据对照，未证明最优或临床可部署 |
| 010–012 | 检索、选择、打包和Judge支持范围问题可以并存；有限语义深读不能断言总体主要瓶颈 |
| 013 | 四个具体机制版本均未过筛选门槛；停止，不换名扩展或追加v2/v3挽救 |
| 014 | Qwen可保留为较小模型研究对象，但未证明非劣、普遍优越或本地／私有化部署性能；复现修订阻塞已关闭 |
| 015 | 双候选理由仲裁失败；evidence_only对照+15只是探索信号，随后由016独立新患者队列检验 |
| 016 | 新6人601条，review452，低于Qwen457，仅比普通repeat451多1；未达到原门槛，停止当前方向，不确认剩余患者 |
| 017 | GT盲单段替换headroom门槛未通过；仅第一阶段执行，未训练utility selector，快速独立审计PASS |
| 018 | 两批1251条离线差距诊断，快速独立审计PASS；支持边界优先研究，真实净headroom仍unknown，不自动启动新实验 |
| 019 | 固定证据支持边界筛查：原低false-S保护门槛未通过，但λ=2在650条开发材料上出现PA/MCC正向网格信号；尚未独立审计 |
| 020 | 固定λ=2在剩余10名development患者879条上双轮确认；总体相对B/U0/O的PA/MCC两轮均正向，仍有false-S/NS与LLM子组边界；尚未独立审计 |

完整任务与正式报告映射见[根README任务表](../README.md#5-current-status)，独立结论见[审计索引](../reviews/README.md)。

## 016正式结果

- [唯一中文主报告](../outputs/016_disagreement_triggered_review_validation/completion_002/report.md)
- [独立审计PASS](../reviews/016_disagreement_triggered_review_validation.md)
- [当前任务入口](../tasks/016_disagreement_triggered_review_validation/CURRENT.md) · [当前成果入口](../outputs/016_disagreement_triggered_review_validation/CURRENT.md)

V4/Qwen各601份有效预测；92条分歧各完成普通repeat与015原版independent-review，509条一致直接保留。正确数V4/Qwen/repeat/review/原发布系统为446/457/451/452/489。review较最强单模型−5、较repeat+1；human NA及患者损失保护条件亦未全部满足。

Qwen为127条硅基流动＋474条阿里云；基础模型跨时段，不能称严格同期单供应商比较。没有触发策略随机对照或全量review；不把错误富集当门控因果证明，不新增医学gold。

全任务历史费用估算＋未知预留21.79039103元／40元；2137条尝试记录含2133份回执与4条无回执未知预留。原暂停、补齐、失败、测试和供应商切换记录全部保持。

## 患者和后续研究

003固定20名探索、40名开发、40名reserved test。020已使用此前剩余10名development患者，因此40名development现均已用于方法开发/确认；40名reserved test仍未用于020或方法选择。001/002已有全体汇总，因此不声称reserved test在任何层面从未被接触；是否开启最终测试需在020独立审计和方法冻结后另行决定。

后续需先说明科研意义、已有失败机制证据、与历史失败路线的实质区别，以及继续／停止门槛。保留负结果，避免只凭少量典型病例扩大实验。

## API现行约定

见[API_POLICY.md](API_POLICY.md)：V4先用硅基流动启用号池，Qwen继续阿里云；全号池明确耗尽后通知用户，后续全部API工作转阿里云。新任务预计累计费用≤80元直接执行，超过80元或无法合理估算先确认；历史预算不改写。当前没有全号池已经耗尽的证据。

## 旧入口的版本含义

部分README、`current_result.md`、旧报告和工具说明已被审计manifest或handoff固定。它们的“未完成／待审／40元／尚未真实调用”等措辞是形成时的记录，保留字节以便重放；现行导航改为链接本页、CURRENT入口及API_POLICY。尤其：

- 016旧`tasks/.../README.md`、`outputs/.../README.md`和`current_result.md`不再作为当前状态入口。
- `docs/aliyun/README.md`是客户端最初交付的冻结说明；后续真实调用、016完成及现行80元规则以[CURRENT.md](aliyun/CURRENT.md)为准。
- 原主报告中的“尚未独立审计”是交审前正文，审计当前状态以[独立审计](../reviews/016_disagreement_triggered_review_validation.md)为准，不改写被审报告。
