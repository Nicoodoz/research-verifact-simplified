# 127 native_reason_data

当前私有版本`dataset_v12_support20261031`：67对AI辅助审读reason，训练63、内部验证4（S21／NS24／NA22）；102条已审、35条待核，3675条原医生标签保留。32名训练／8名内部验证划分不变。

最新12条均来自此前未处理的原32名训练患者命题，新增9对（S5／NS2／NA2），3条因时点、地点或适应证边界保留问题；一次时间解释在交叉检查后撤回，原记录及更正均保留。旧58对及编码检查直接复用，只编码新增9对。

本轮三批累计新增27对，均只留后续，不进入已完成138或正在运行140。新数据没有分类收益证明；不凭教师改GT，不强编解释。主要审读者完整阅读reference，根模型交叉核对新claim、理由、引文及边界；不称为医师认证。

[最新批次](../../outputs/127_native_reason_data/new_batch_support_20261031/report.md) · [统计](../../outputs/127_native_reason_data/new_batch_support_20261031/summary.json) · [总报告与历史](../../outputs/127_native_reason_data/report.md) · [数据合同](DATA_CONTRACT.md)

构建继续复用prepare127.py；新版本不覆盖旧目录。临床正文、reason、草稿和完整审读记录只存.local_models/127_native_reason_data/。
