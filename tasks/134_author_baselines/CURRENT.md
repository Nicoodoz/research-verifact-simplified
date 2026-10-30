# 134 author_baselines：未微调1817完成，适配器继续

author_base9b已返回1817条，1806有效、11截断；MCC .3425、正确1222、false-S44/361，NA仅1/241正确。较低false-S不能脱离NA损失称优。

author_lora9b正在补新增1317。最近完整配对为原500：共同495，适配器正确392、MCC .5820、FS52/178；相对同权重104接口少对2、FS少3。新旧原始结果全部保留，无重发。

仍以23:40起GPU16元／API80元累计，不自动关机或释放。下一GPU研究等待完整统一比较。

[未微调完整阶段](../../outputs/134_author_baselines/base1817_stage.md) · [当前报告](../../outputs/134_author_baselines/report.md) · [实时进度](../../outputs/134_author_baselines/progress.md)
