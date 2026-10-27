# 101价格核实（2026-10-27）

重新读取当前端点的[千问AI官方模型价格](https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices)，deepseek-v4-flash-0731忙时输入/输出/隐式缓存输入为3/9/0.3元每百万token，闲时为1.5/4.5/0.15。与[百炼价格表](https://help.aliyun.com/zh/model-studio/model-pricing)同名模型一致；旧deepseek-v4-flash详情URL已重定向，不能用该地址的模型总览代替价格。

本轮按忙时估计直接执行；当实际请求跨时段或时段无法确认时按高价。原价计全部预检、基线补齐、两复核、重复、重试和未知/在途，不用促销赠金或旧130元额度扩容。累计硬限30元，单次最大预留独立于全任务历史usage预测；费用为usage估算而非账户实扣账单。

初版预算plan约25.23元，不以所有调用均输出8192 tokens夸大全轮预计支出；8192仍用于每个在途请求的事务安全上界。初版缓存含新200中8条；明确端点核查更正后只复用其中3条，另5条补齐，不改200条ID。无效成功回执保留，不重发择优。补齐后按282个实际触发和每条基线真实prompt usage加新提示长度差、开发输出usage重估，总计约27.33元，见trigger_freeze与remaining_forecast；不以复核正确率估预算。
