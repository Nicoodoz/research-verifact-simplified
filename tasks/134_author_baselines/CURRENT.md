# 134 author_baselines：160初筛完成，继续500及1817

两个9B各完成160首回执；严格共同158条，author_base9b／author_lora9b正确93／120、MCC .3650／.5117、false-S 8／19（非S57）。适配器有质量收益与风险代价；与104接口120正确数相同，仅NS/NA交换1条。未微调NA召回0，不把低false-S当独立胜出。

每臂首阶段复用8、补152；另外12条匹配缓存随后复用。未微调2条截断保留，适配器无无效但18条缺reason。当前继续补齐原500及完整1817，不启动新的改进推理或训练。

GPU16元／API80元均从2026-10-30 23:40起另账；无新增收费API，不自动关机或释放。

[当前报告](../../outputs/134_author_baselines/report.md) · [进度](../../outputs/134_author_baselines/progress.md) · [冻结方案](PROTOCOL.md)
