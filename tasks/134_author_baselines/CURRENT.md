# 134 author_baselines：准备完成，接续正式推理

固定1817条／20名选型患者。paper_r1完整复用；author_base9b、author_lora9b各复用20条配置匹配的原生诊断回执，各缺1797条。旧103的180条因thinking预算不同不合并。

原作者模板与固定上游函数返回值一致；两个9B统一BF16、关闭thinking、greedy、768输出上限，完整reference不截断。当前无新训练或收费API。

本轮GPU从2026-10-30 23:40起累计，上限16元；API另计，上限80元。不自动关机或释放。当前实时数量、阶段和费用见[进度](../../outputs/134_author_baselines/progress.md)。

[方案](PROTOCOL.md) · [缓存盘点](../../outputs/134_author_baselines/cache_inventory.json) · [准备结果](../../outputs/134_author_baselines/preparation.json)
