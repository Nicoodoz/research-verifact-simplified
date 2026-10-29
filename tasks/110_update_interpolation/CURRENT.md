# 110当前状态

COMPLETE_WITH_TRADEOFF_NO_AUTO_SHUTDOWN

110 update_interpolation完成，无新增训练/API。109实际192条诊断证实训练NA也丢失（0/64，32正确NA保留全误伤，真标签CE .005282→.485546）。两固定有效BA插值各500全有效：quarter自然MCC.4738/PA77.75%/false-S13，压力.4303/66%/14；half自然.4636/76.50%/11，压力.4456/68%/13。相对107有真实压力增量，但自然质量下降，尚无整体优势，未通过预写综合保留参考；保留107，不自动扩大/111或升级默认。关键结果和两个rank32适配器已回传。用户执行中撤销自动关机，保护已停、未发关机命令，实例保留开机；租金继续累计，费用见110记录。

本轮从2026-10-29 11:51按1.58元/小时累计，GPU任务上限5元。192诊断、32NA两端真实标签CE和两个点的1000条完整评价均结束；关键结果12:39:18已全部回传，彼时租金约¥1.2721，API0。用户撤销自动关机后已停止远端guard9317并核验，回传触发不发送关机；实例按要求保留开机，等待费用继续，不释放/删磁盘。

quarter压力较107净增8条正确NS，NA未损失、false-S−2；自然损失7条正确S、3条NA，NS净增2、false-S+1。half压力NS净增16伴NA净损失6，自然S/NA净损失9/10。不能称整体优于107，也不能说完全无局部增量。两个点均未通过预写综合保留参考，当前不扩大；是否接受quarter取舍并做一项最小确认，须用户新决定。不追加系数、种子、普通回放、loss或训练，不自动111。

准确cat共248层，rank32、源FP32因子、单BF16底座；0/1各3真实输出完全匹配。旧107/109检查点、完整状态与结果均保留。新适配器和全部原始结果在.local_models/110_update_interpolation/evidence/results/，不提交私有原文/回执/凭据/权重/缓存。基线完整500直接复用，没有新训练。

本轮正式结果与状态按用户明确授权正常双仓库发布，实际提交及远端核验以交付回执和Git历史为准。完整起点a534a84c、精简7e00f1d8，原工作区无无关改动；不force push或改写历史。

[最终报告](../../outputs/110_update_interpolation/final_report.md) · [完整指标](../../outputs/110_update_interpolation/comparison.json) · [诊断](../../outputs/110_update_interpolation/diagnostic192.json) · [费用](../../outputs/110_update_interpolation/cost_status.json)
