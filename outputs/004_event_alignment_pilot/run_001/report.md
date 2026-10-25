# 004：实验准备结果

状态：**仅完成离线准备，真实推理尚未开始，尚无方法效果结果。**

按 003 冻结的 seed + patient ID 哈希顺序选开发组前 6 名：93147, 29426, 85689, 91315, 45979, 98790。没有按标签或旧预测对错选样本。患者清单中的数值排序不是本次抽取顺序。其余 34 名开发患者及 40 名保留测试患者不进入本次队列、请求或评价。

| 作者 | 有效 claims | S | NS | NA | 已知时间冲突标记 |
| --- | ---: | ---: | ---: | ---: | ---: |
| llm | 181 | 166 | 7 | 8 | 29 |
| human | 240 | 161 | 24 | 55 | 48 |

共 421 条有效命题，排除 1 条 invalid，排除 ID 另存。主分析保留全部时间冲突行；预设敏感性分析对三臂同时排除这些 ID，不改日期或医生标签。

每条命题三种方式各调用一次，计划 1263 次。三臂使用同一实际 Judge、同一完整 reference、相同解码参数和 2,048 输出 token 上限，总输出上限暂计 2,586,624 tokens。该数值以最终服务确实将全部生成 token 计入同一上限为前提，不是费用估算。

普通结构化与事件核对均为五项检查、相同 JSON 格式、合计最多 200 个解释词；常规方式使用自由解释和空 checks，也可使用相同解释词数。相同上限不保证实际 token 或隐藏推理量相同。静态长度见 summary.json / request_schedule.csv；实际 token、费用、上下文适配和 thinking 配置尚待选定 Judge 后核实，禁止静默截断证据。

证据取自 release 的 R1-70B / rater-121（sentence facts、N100、rerank、absolute_time、current admission、deduplicate=True）。保存 reference 原文及 SHA-256，不补检索、不重新筛选日期。实得块数见 summary.json，不假设每条恰好 100 块。模型只看到命题和 reference，不看到 GT、既有预测、作者类型、parent 或完整 BHC。

主要比较为 event_alignment − structured；event_alignment − routine 和 structured − routine 为辅助比较。分别对 llm/human 调用 002 的 evaluate / paired_compare：valid-only、完整队列、三分类 PA/AC1/MCC、1,000 次患者 bootstrap，同时报告各类性能、非 S→S、NS↔NA、正确变错/错误改正和逐患者结果。六名患者只作探索；尤其 LLM 少数类很少，不以置信区间或单个净增益声称机制成立。

若事件核对不优于普通结构化，或只是通过全面变严增加 S→NS/NA，或收益伴随明显更高实际预算，则优先假设未得到清晰支持。原作者发布预测单列为历史参照，不能代替本轮 routine 重跑；三种新判断均须由同一实际模型执行。

待决定：Bedrock 可用的精确模型/版本、区域与推理配置；费用上限。待完成：本地 tokenizer 或获批后的计数接口核实所有请求的上下文与 token 预算、仅用虚构材料验证服务适配器。最后需用户明确确认真实推理，届时另存服务绑定后的新准备版本，不覆盖本记录。

文件：cohort_*.csv 为评价队列；inputs.jsonl 为本地命题和证据；request_schedule.csv 为固定调用顺序与哈希；historical_predictions_*.csv 为发布预测；prompts/ 与 config.json 为快照。虚构 dry-run 的分数不属于 VeriFact 实验成绩。
