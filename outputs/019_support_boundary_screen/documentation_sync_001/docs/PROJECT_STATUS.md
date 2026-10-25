# 项目现状总览

更新：2026-09-16。当前状态入口；历史版本中的“待审／暂停／下一步”不覆盖本页与最新独立审计。

## 当前结论

**018当前：** 018完成010/016两批12名已暴露患者1251条离线差距诊断：原VeriFact独对156、C48＋V4独对84，净差+72主要来自S召回，同时false-S为79/27且原系统MCC点估计更低。010固定V4后发布reference净−15，不支持将发布系统PA优势主要归于reference。优先研究Judge支持边界；真实可优化净headroom仍unknown。78例深读，186条方向性机制未充分深读，保留unknown；0新增API，无新优化或新患者实验。快速独立审计PASS，可冻结／结项，见[018审计](../reviews/018_verifact_gap_attribution.md)。见[中文主报告](../outputs/018_verifact_gap_attribution/report.md)与[交审材料](../outputs/018_verifact_gap_attribution/audit_handoff.md)。

**017历史结果：** 017完成12名已暴露患者192条GT盲证据干预：19条稳定错误中稳定救回0条，160条稳定正确中破坏3条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。快速独立审计PASS，可冻结／结项，见[017审计](../reviews/017_verification_supervised_evidence_utility.md)；[唯一中文主报告](../outputs/017_verification_supervised_evidence_utility/report.md)与[交审入口](../outputs/017_verification_supervised_evidence_utility/audit_handoff.md)。

001–018已完成并有相应独立审计依据，016快速审计PASS、可冻结／结项。审计通过不等于方法有效。最终论文方法和贡献仍未确定，不自动启动下一实验。

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

完整任务与正式报告映射见[根README任务表](../README.md#5-current-status)，独立结论见[审计索引](../reviews/README.md)。

## 016正式结果

- [唯一中文主报告](../outputs/016_disagreement_triggered_review_validation/completion_002/report.md)
- [独立审计PASS](../reviews/016_disagreement_triggered_review_validation.md)
- [当前任务入口](../tasks/016_disagreement_triggered_review_validation/CURRENT.md) · [当前成果入口](../outputs/016_disagreement_triggered_review_validation/CURRENT.md)

V4/Qwen各601份有效预测；92条分歧各完成普通repeat与015原版independent-review，509条一致直接保留。正确数V4/Qwen/repeat/review/原发布系统为446/457/451/452/489。review较最强单模型−5、较repeat+1；human NA及患者损失保护条件亦未全部满足。

Qwen为127条硅基流动＋474条阿里云；基础模型跨时段，不能称严格同期单供应商比较。没有触发策略随机对照或全量review；不把错误富集当门控因果证明，不新增医学gold。

全任务历史费用估算＋未知预留21.79039103元／40元；2137条尝试记录含2133份回执与4条无回执未知预留。原暂停、补齐、失败、测试和供应商切换记录全部保持。

## 患者和后续研究

003固定20名探索、40名开发、40名reserved test。前30名开发患者已使用，剩余10名保留；016没有进入后续冻结确认。reserved test不用于方法选择，不能为结果重抽患者。001/002已有全体汇总，不声称保留测试组从未被接触。

后续需先说明科研意义、已有失败机制证据、与历史失败路线的实质区别，以及继续／停止门槛。保留负结果，避免只凭少量典型病例扩大实验。

## API现行约定

见[API_POLICY.md](API_POLICY.md)：V4先用硅基流动启用号池，Qwen继续阿里云；全号池明确耗尽后通知用户，后续全部API工作转阿里云。新任务预计累计费用≤80元直接执行，超过80元或无法合理估算先确认；历史预算不改写。当前没有全号池已经耗尽的证据。

## 旧入口的版本含义

部分README、`current_result.md`、旧报告和工具说明已被审计manifest或handoff固定。它们的“未完成／待审／40元／尚未真实调用”等措辞是形成时的记录，保留字节以便重放；现行导航改为链接本页、CURRENT入口及API_POLICY。尤其：

- 016旧`tasks/.../README.md`、`outputs/.../README.md`和`current_result.md`不再作为当前状态入口。
- `docs/aliyun/README.md`是客户端最初交付的冻结说明；后续真实调用、016完成及现行80元规则以[CURRENT.md](aliyun/CURRENT.md)为准。
- 原主报告中的“尚未独立审计”是交审前正文，审计当前状态以[独立审计](../reviews/016_disagreement_triggered_review_validation.md)为准，不改写被审报告。
