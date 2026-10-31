# 127 native_reason_data

当前资产为私有 `dataset_v11_followup20261031`：58对AI辅助审读reason，训练54、内部验证4（S16／NS22／NA20）；90条已审、32条问题保留，3675条原标签全部保留。32名梯度训练／8名内部验证患者划分不变。

2026-10-31这批来自18条此前未处理的训练病例，全部有医生备注供核对；主要审读者先看完整实际reference，作者历史理由和备注只作为核对来源，不替代当前输入。接纳10条（S4／NS2／NA4），8条不强编理由。所有新10条均不在105理由集、127旧审读集或此前6例教师试查中，按患者、claim、reference检查也无旧样本重复。复用原40对，只对新增10条做CPU编码，完整输入和原GT均保留。

随后再审12条未处理训练病例，接纳8条（S1／NS3／NA4），4条待核；原50条检查复用，只编码新增8条。两批共新增18条理由，均留后续。

本批尚未训练，没有分类收益证据；不改变正在运行的138（冻结v9的36条训练理由）。后续是否使用新增数据，依据138及其他真实分类结果决定。原始草稿、交叉复核撤回记录和未决项留在私有目录，不把AI辅助理由称为医生标注。

[当前简报](../../outputs/127_native_reason_data/new_batch_followup_20261031/report.md) · [统计](../../outputs/127_native_reason_data/new_batch_followup_20261031/summary.json) · [总报告与历史](../../outputs/127_native_reason_data/report.md) · [数据合同](DATA_CONTRACT.md)

构建与汇总继续复用 `prepare127.py`、`summarize127.py`，新版本不得覆盖旧目录。实际临床文本、reason与完整审读记录仅保存在 `.local_models/127_native_reason_data/`。
