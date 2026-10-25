# 017：verification-supervised evidence utility

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/017_verification_supervised_evidence_utility/report.md)。 独立结论查[审计末尾](../../reviews/017_verification_supervised_evidence_utility.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

先检查GT盲、重复测量的单段替换是否有足够selection-fixable空间；通过才训练固定低容量pairwise ranker，再通过patient-disjoint选择才确认剩余10名开发患者。不修改claim、C48打包器或Judge prompt，不新增医学gold。

[事前协议](../../outputs/017_verification_supervised_evidence_utility/protocol_001.md)为实施和停止依据。001–016原始数据、代码、回执、主报告与审计保持。017总预算80元跨所有阶段累计，V4先使用硅基流动启用号池。

## 当前结果：第一阶段停止，待独立审计

192条／12名已暴露开发患者，五条件各两次，共1572份有效回答。19条稳定错误没有稳定rescue；160条稳定正确中3条稳定harm。训练组仅2个非零配对；未通过事前门槛。没有训练selector，没有使用剩余10名开发患者或reserved test。费用估算与未知预留¥13.37319060／¥80。

唯一必读：[中文主报告](../../outputs/017_verification_supervised_evidence_utility/report.md)。[审计交接](../../outputs/017_verification_supervised_evidence_utility/audit_handoff.md)说明真实范围、局限和自查证据；执行者不宣布独立PASS。

## 离线重放

在仓库根目录和`research-verifact`环境中执行，输出目录必须全新：

```powershell
python -B tasks/017_verification_supervised_evidence_utility/verify017.py --output outputs/017_verification_supervised_evidence_utility/verification_AUDITOR_FRESH
python -B -m unittest discover -s tests -p test_utility017.py
python -B -m unittest discover -s tests -p test_evaluation.py
```

`verify017.py`重建GT盲抽样／证据动作／特征／body／重复缓存，核对原始回执和费用，按002重放32份分析文件，并检查001–016受保护历史。它不调用API。主报告数值及解释可另用`report017.py --output <全新目录>/report.md`重新渲染，与正式report.md比对；当前报告渲染依据见`verification_report_001/report_sources.json`。初版`report_source_manifest.json`保留其形成时的renderer指纹，不作为当前代码约束。

`prepare017.py`、`run017.py`和`batch017.py`是本次已结束真实执行的记录，**不是待续跑任务**；`learn017.py`是冻结的条件预案，gate为false时禁止训练。没有下一轮收费授权自动重启该版本。
