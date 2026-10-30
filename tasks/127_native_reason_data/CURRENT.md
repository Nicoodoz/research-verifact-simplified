# 127 native_reason_data

当前累计20条可靠配对（S7／NS7／NA6），训练16条、内部验证4条。继初始24条试审后，针对已有医生备注再审8条，接纳5条、保留3条问题。新数据在`dataset_v2_doctor_extension`，原`dataset_v1`与原15条保持不变；全部3675条原label_only仍保留。仅新增5对做CPU编码检查，旧15对复用已通过结果。[增量统计](../../outputs/127_native_reason_data/doctor_extension_summary.json)

仅做数据与CPU接口准备；不启动reason监督训练，不改变正在运行的120。原40名训练患者沿用32名梯度训练、8名内部验证划分；选型20人及确认40人不用于本阶段。

固定24条三类各8条的语义试审：其中12条来自105已有配对，另12条优先覆盖既有教师分歧和106边界问题。该批富集困难样本，不能用通过率估计全池质量。先独立审读当前完整reference和写草稿，再对照旧理由；缺少可靠依据时保留医生GT和label_only，不生成配对reason。

初始试审产生15条可用理由、9条待核。旧105的12条已有理由没有展示实质语义提升；当时新增可用3条为S2/NA1。后来基于医生备注的有限补充增加5条配对，其中2条在旧105中已有类似解释；不是把111条备注批量转成理由，也不为达到196/512而扩写。

入口：

```powershell
python tasks/127_native_reason_data/prepare127.py --annotations .local_models/127_native_reason_data/pilot24_reviewed.jsonl --out .local_models/127_native_reason_data/dataset_v1
python tasks/127_native_reason_data/summarize127.py --reviews .local_models/127_native_reason_data/pilot24_reviewed.jsonl --dataset .local_models/127_native_reason_data/dataset_v1
```

`dataset_v1`已存在时不要覆盖；新修订另存版本。实际数据、reason、引用原文与审读记录只在私有目录。公开交付：[简短报告](../../outputs/127_native_reason_data/report.md)、[覆盖统计](../../outputs/127_native_reason_data/summary.json)、[去正文状态](../../outputs/127_native_reason_data/review_status_sanitized.jsonl)、[接口合同](DATA_CONTRACT.md)。

CPU通过不等于9B分类有效。当前小批不支持宣称已改善105的数据语义质量，也不足以单独支持新训练；继续120原定任务，不追加本方向GPU实验。
