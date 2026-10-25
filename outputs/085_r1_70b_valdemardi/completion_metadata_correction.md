# formal_completion.json的续跑计数更正

首次正式执行从Stage B既有3条成功结果开始，期间执行终端中断；当时20个正式位置已有HTTP200且没有未完成attempt，之后按同一请求ID续跑。续跑进程启动时加载了早期runner代码，将“本进程启动时已成功的20条”错误命名为`initial_AB_HTTP200_slots`，并将本进程新完成的340条写为`new_HTTP200_slots`。`runner_wall_seconds_excluding_initial_AB`也只覆盖续跑进程，不能当作整个正式阶段的墙钟时长。

这些是**完成摘要的字段命名和跨进程计数错误**，不涉及模型请求、选择、raw回执或评价标签。原`formal_completion.json`保留不改写，原生attempt链完整保留；[正式对账](formal_reconciliation.json)逐条依据保存的`request.stage`、HTTP状态、请求/响应SHA重建：**Stage B复用3条，新增formal HTTP200 357条，全部360条唯一成功，0重试、0未知回执**。后续报告、自检及费用汇总以正式对账为准，不引用误名字段作为实验调用总数。执行代码已修正用于将来安全续跑；当前任务不重发任何请求。
