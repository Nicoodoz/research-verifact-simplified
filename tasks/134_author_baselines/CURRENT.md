# 134 author_baselines：500阶段完成，继续新增1317

两臂各500首回执已完成，共同有效495。author_base9b／author_lora9b正确304／392、MCC .3945／.5820、false-S21／52（非S178）。适配器有质量收益和NS／false-S代价；相对104接口120少对2条、少3次false-S。

未微调3条截断、适配器2条JSON错误均保留；适配器另有76条有效标签缺reason。paper_r1直接复用；正在补两臂新增1317，不启动其他GPU实验。

GPU16元／API80元从2026-10-30 23:40起累计；不自动关机或释放。模型本身与输入优化的下一步须由完整基线和剩余预算决定。

[阶段报告](../../outputs/134_author_baselines/report.md) · [进度](../../outputs/134_author_baselines/progress.md) · [冻结方案](PROTOCOL.md)
