# 085 Valdemardi当前状态

**正式执行已完成（2026-09-27）：** 180条/21名已暴露development患者，R1-B/F4各180次HTTP200，Stage B复用3＋新增357，0重试。四臂raw共同有效177条；R1-F4比V4-F4 raw净+13正确但false-S多8/30、MCC仅+0.0033。全180条最终系统R1-F4＋Frozen PriorG比当前V4-B＋G仅净+1，MCC 0.5423对0.5881、false-S 11对6/30；不升级默认。主自检1853项、最终系统补充61项PASS，独立审计未执行。GPU时价和租金未知。详见[正式报告](report_formal.md)与[续跑计数更正](completion_metadata_correction.md)。

下方为A/B结束时的历史快照：

- A/B预检完成：1条虚构、3条085A冻结病例，4/4首次HTTP200，0重试；三条B已占正式位置。
- 360条队列仅改model ID；剩余B179/F4 178未调用。服务ID及20K上下文由loopback实测；远端checkpoint字节和vLLM版本未独立核验。
- Valdemardi tokenizer与旧官方审计不同，全部360条本地输入少2 token；A/B的服务输入token与本地逐条一致，最长F4加8192输出预算为17884。
- 预测串行约2.85小时，50%规划余量约4.27小时；当前实例小时价格未知，GPU租金不估。
- 0评价GT、0正式批量、0系统性能比较；默认系统不变，等待用户看forecast并另行授权正式批量。
- 自检61项、离线单测5项PASS；独立审计未执行。详见[报告](report.md)与[forecast](forecast.json)。
