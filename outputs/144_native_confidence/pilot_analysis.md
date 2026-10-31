# 144原生分支置信度：pilot

状态：PILOT_COMPLETE_NO_PERFORMANCE；规定评分27、收到27、有效27、缺失0、无效0。

分数为logit(S)−logit(Not)，是首标签分支分数，不是已校准三分类概率。实际零分数保留，缺失或无效分数不填0。

Pilot/coverage-only job: receipt completeness does not authorize performance conclusions.
未生成分类效果、送审曲线或按部分数据挑选的点。

## 评分资源与尝试

成功记录forward秒数：已记录27项，总计91.38686272501945；原prompt tokens记录27项，总计227604。

worker墙钟按时间区间并集汇总：1段，总计162.9301秒；模型加载52.0165秒，准备19.1117秒。内外层完成/退出记录即使端点不同，嵌套或重叠也只计一次，不重叠运行相加；原记录保留在JSON。

controller墙钟单列：166.2059秒。控制器包含worker运行区间，不能与worker墙钟再次相加。

实际batch分布：{'1': 27}；尝试事件：{'started': 27, 'completed': 27}。

未配到完成事件的前向尝试0次；其forward成本未知时不填零，退出墙钟仍单列。

成功forward总和不是完整成本：加载、token编码、等待、失败/在途尝试及进程墙钟按runtime/attempt原始记录另列；字段缺失为未知，不能当作零。理论上未来可在原生生成同一prefill同步捕获分支logits，但本项目尚未实现或测定该部署成本；当前额外评分需要实际前向。

这是既有开发患者上的固定回顾，不是独立测试或CP/风险保证。当前分析新增GPU/API调用为0，已有评分任务的GPU成本须按全尝试账本计入。
