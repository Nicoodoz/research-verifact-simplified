# 104辅助语义核查目录价

2026-10-27在首次收费请求前只读核对[千问AI模型价格](https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices)：`deepseek-v4-flash-0731`忙时输入/输出/缓存输入每百万tokens为3/9/0.3元，闲时为1.5/4.5/0.15元。[阿里云模型价格](https://help.aliyun.com/zh/model-studio/model-pricing)说明忙时为北京时间08:00—22:00，闲时为22:00—次日08:00；思维链和最终回答均属输出计费。

只使用当前`.env.aliyun`授权的`https://maas.qianwenaiapi.com/compatible-mode/v1`，固定0731，不切模型/供应商/key。不是Token Plan渠道折扣。计划按全忙时、无缓存以及UTF-8字节上界＋2048模板余量、8192输出＋32预留；20元全任务硬上限，运行线18元，另留2元异常余量。已成功HTTP200（含坏格式/负面核查）不重发；失败最多3次尝试，各次独立预留。未知/在途不无据释放。

结算公开记录使用实际usage、开始/结束UTC映射UTC+8；仅两端均闲时且耗时不足一小时按闲时，否则按忙时。预算统计一律不扣缓存；缓存目录价另列可比估计，不据此加样。官方时间戳账单未取得，因此这些是目录价估算，不是账户实扣证明。价格页只读检索不属于收费completion。
