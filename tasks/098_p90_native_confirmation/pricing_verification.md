# 098目录价核实（2026-10-26）

本任务实际路由为已授权https://maas.qianwenaiapi.com/compatible-mode/v1，固定deepseek-v4-flash-0731。不换成名称接近的deepseek-v4-flash或v4.1，不调用智能路由。

本次重新在线核对[官方模型调用价格](https://help.aliyun.com/zh/model-studio/model-pricing)：北京0731输入/输出忙时3/9、闲时1.5/4.5元每百万token，思考计入输出；北京时间22:00–08:00为闲时，其余为忙时。旧模型详情URL当前重定向到模型总览，故不只依赖旧URL。本次[官方智能路由备选表](https://help.aliyun.com/zh/model-studio/model-routing)也列出同名模型忙时输入/缓存输入/输出3/0.3/9及闲时1.5/0.15/4.5，但098不使用该路由功能。

实际账本按逐次usage和起止UTC时段核算原目录价；跨价格边界保守按忙时。未返回可靠usage或模型不符则保留整次最大预留。缓存只按官方缓存输入目录价计费，不按促销、赠金或账户余额扩大50元额度。完整请求预留按忙时输入UTF-8字节上界+2048封装token、最大允许输出计算，所有在途同一事务累计。

预算预估使用097简洁任务的usage摘要与098实际输入字符数，额外保守放大；不是直接照搬旧每次费用。最终选择自然400、压力NS/NA各50、F80、四臂重复60，共2120次目标请求，另2次Q构造。500条方案在同一保守闲时计划下超过43元计划线，400条方案约42.05元，留下约7.95元至硬限，用于波动、重试和未知；首批8例完整四臂事前固定忙时发送，其余闲时，不按先跑成绩改变规模。

实际费用与成功覆盖以cost_ledger.json及attempt_ledger.jsonl为准。本文件不是账户实扣账单或旧/新端点科学等价证明。

## 当前端点的直接文档补核

首批32次正式请求完成后的等待阶段，进一步从新平台文档首页导航到[千问AI模型价格](https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices)，直接核对0731忙时输入/输出/隐式缓存输入3/9/0.3及闲时1.5/4.5/0.15，均与冻结账本一致。[千问AI计费说明](https://platform.qianwenai.com/docs/developer-guides/getting-started/pricing)解释实际按量计费；[当前端点接入](https://platform.qianwenai.com/docs/developer-guides/getting-started/first-api-call)确认本任务base URL。该补核不改变费率、预算、方法、样本或判据，没有新增收费调用，不将业务空间路由推断为已验证的历史科学等价。
