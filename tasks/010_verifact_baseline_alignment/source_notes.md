# 010 来源和解释边界

010定向阅读002统一协议、run_003正式报告及独立审计；009正式报告、C48配置、生成/回执/评分实现和2026-09-15修订独立复核末尾。没有重做001–009独立审计，也没有重新进行临床标注或系统文献综述。

|来源|亲自核对的内容|不能据此推出|
|---|---|---|
|release rater_configurations.csv / model_metadata.csv|目标配置唯一为v1.1.0-rater-121；R1-70B、sentence、N100、rerank、absolute_time、current admission、去重。原Judge为casperhansen/deepseek-r1-distill-llama-70b-awq，辅助结构化模型为Llama-3.1-8B量化版本|不能把原发布系统当同一V4-Flash Judge，或只将成绩差异归于检索|
|release verdicts.parquet → reference_payloads.parquet|650个proposition、对应rater、模型及reference_id逐一连接；payload哈希等于reference_id，发布verdict与002导出一致|reference不是医生gold evidence；同名配置不自动代表其他Judge收到相同payload|
|009 confirmation_001|C48最终reference和完整body原样复用；全部650条valid claims及243/407作者分母不变|旧C48答案不是010同期对照，不能用旧答案代替新生成再把差异全归于reference|
|[固定作者reference_context.py](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/reference_context.py)，本地007来源快照|_query体现按配置检索、去重/重排/top_n等步骤；absolute_time输出Date、Time、Category、Description。sort_reference_context_by_time按CHARTDATE_TS、完整CHARTTIME_TS、STORETIME_TS排序，显示日期取CHARTDATE、时刻取CHARTTIME|源码快照不证明release实际由该版本全部生成；类默认top_k不能当发布运行实际候选容量，缺失原索引/源Feather/排名不伪造|
|010全量metadata诊断|274份发布reference有可见Date+clock顺序逆向，共302相邻逆向；用匹配原note的完整CHARTTIME核对，302处都可与完整时间排序相容。两臂650个住院总头完全相同|不能仅由显示逆向宣布作者排序代码失效。Date和Time来自不同日期字段时，显示组合仍可能使读者/Judge误解，但对标签影响尚需对照|
|010逐字note追溯|使用同患者、Date、Category和归一化空白正文匹配，再用已知Time/Description约束候选；VF不直接给note ID，仍有多重匹配，2处同一事实未逐字定位。C48显式ID和原位置均可查|匹配得到的note数量不是完整医学覆盖率；未匹配不证明内容虚构，短文本或重复条目不自动无关|
|[硅基流动日期公告](https://docs.siliconflow.cn/docs/release-notes/overview)及[价格页](https://siliconflow.cn/pricing)，2026-09-15|V4-Flash峰时输入3/缓存.3/输出9元每百万，02–08北京半价，沿用已核对计费函数；本任务没有repetition_penalty字段|公开usage估算不是账单，服务模型别名不是不可变权重版本|

有些009缺失在发布reference中能看到：N071后期Definity结果、N430同日500cc×2、N561/N563带MRI身份的结果、N585目标日右下肺塌陷。也存在反例：N394神外具体意见在C48中但不在发布reference；N527两套最终材料均未保留已知的明确thrombophlebitis problem list。N302发布包提供另一时间的明确液体复苏改善记录，不是简单恢复009的150mL护理锚点。N644两套均有建议、实施/继续及回顾证据，不能预设其改判是召回收益。此处是已阅读输入的观察，最终解释还需与010完整输出对照。

发布reference正文平均10,319字符、C48为6,488；带metadata的总长度约22,255／8,047。输入总长度差异大于临床正文差异，不能把两种“长度”混用。更广日期/note覆盖、更多metadata、不同片段单元和更多背景同时存在；本任务不做新包装方法或将其打散后归因。
