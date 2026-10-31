# 144原生分支置信度：old500

状态：COVERAGE_ONLY；规定评分713、收到232、有效232、缺失481、无效0。

分数为logit(S)−logit(Not)，是首标签分支分数，不是已校准三分类概率。实际零分数保留，缺失或无效分数不填0。

Prescribed scoring target incomplete/invalid; no performance on the scored subset.
未生成分类效果、送审曲线或按部分数据挑选的点。

## 评分资源与尝试

当前汇总分数对应耗时（含复用）：232条分数中232条有耗时，总计381.5518秒；原prompt tokens记录232项，总计1929335。如有复制的历史分数，其耗时包含在此总和中；不能据此直接认作本段新增计算。

本段新增completed事件数：未记录；其中0项有forward耗时，合计NA秒。仅按本段attempts中的completed事件计，不将复用JSON的seconds再次计为新forward。

运行完成元数据尚未记录reused_score_N/new_forwards。

本段worker墙钟按时间区间并集汇总：1段，总计27.7017秒；模型加载NA秒，准备NA秒。内外层完成/退出记录即使端点不同，嵌套或重叠也只计一次，不重叠运行相加；原记录保留在JSON。

controller墙钟单列：30.1505秒。控制器包含worker运行区间，不能与worker墙钟再次相加。

实际batch分布：{'1': 232}；尝试事件：{}。

未配到完成事件的前向尝试0次；其forward成本未知时不填零，退出墙钟仍单列。

汇总分数对应的forward总和不能作为本段新增付费时间。新增forward本身也不是完整成本：加载、token编码、等待、失败/在途尝试及进程墙钟按本段runtime/attempt原始记录另列；字段缺失为未知，不能当作零。理论上未来可在原生生成同一prefill同步捕获分支logits，但本项目尚未实现或测定该部署成本；当前额外评分需要实际前向。

这是既有开发患者上的固定回顾，不是独立测试或CP/风险保证。当前分析新增GPU/API调用为0，已有评分任务的GPU成本须按全尝试账本计入。
