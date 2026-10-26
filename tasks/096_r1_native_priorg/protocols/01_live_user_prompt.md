继续当前 research-verifact 项目。

用户已经完成本任务的零API准备。不要恢复被取消/删除的旧096构造修复任务。
本轮研究方向已经重新冻结为：

“R1 raw / V4 raw / Original VeriFact 公平比较，以及 PriorG 是否能通过相同配方重新适配迁移到 R1。”

本轮禁止：
- F4
- Qwen
- contrast/minimal-contrast继续开发
- 新检索方法
- 新prompt搜索
- 新阈值网格搜索
- 全9065 R1推理
- 为了得到赢家而事后更换样本、损失、先验或参数范围

==================================================
一、当前R1服务
==================================================

AutoDL已启动：

R1_BASE_URL=http://127.0.0.1:18000/v1
R1_MODEL=Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ
R1_API_KEY=EMPTY

远端实际环境：
- NVIDIA A800 80GB PCIe
- vLLM 0.10.1.1
- ModelScope下载的
  Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ
- AWQ 4-bit
- max_model_len=20000
- reasoning_parser=deepseek_r1
- temperature=0
- top_p=1
- formal max_tokens=8192
- 服务名必须精确匹配上述R1_MODEL

沿用085 Valdemardi实验的调用、解析、receipt、resume和成功请求不重发原则。
可以复用085代码，但不要修改历史085工件；新任务单独建立目录。

先在Codex实际执行环境访问：

GET http://127.0.0.1:18000/v1/models

如果无法访问，立即停止并只报告 R1_ENDPOINT_UNREACHABLE。
不要修改AutoDL服务或SSH配置。

==================================================
二、研究问题
==================================================

RQ1：
在一个分布合理、预先冻结、非全量的自然评价面板上，
R1-B raw、V4-B raw、Original VeriFact发布结果分别表现如何？

重点不是只看PA，必须同时报告：
- correct / N
- PA
- MCC
- Gwet AC1
- Macro-F1
- S recall
- NS recall
- NA recall
- false-S count
- false-S rate

并做患者cluster bootstrap配对区间。

RQ2：
R1 raw与V4 raw的错误结构是否不同？
分析：
- rescue / harm
- GT类别转移
- human / llm author strata
- 患者胜/负/平
- false-S
- NS / NA行为

不能把输出差异直接解释成模型内部机制。

RQ3：
V4上冻结的PriorG参数是否能直接迁移到R1？

比较：
- R1 raw
- R1 U0（诊断）
- R1 + existing V4 Frozen PriorG

这里的“Frozen PriorG”必须是现有V4开发出的原参数原样迁移，
不得用R1评价结果重拟合。

RQ4：
如果使用“相同配方、相同监督范围、相同参数数目”，
重新为R1拟合PriorG，性能是否改善？

比较：
- R1 raw
- R1 + V4 Frozen PriorG
- R1 + R1-adapted G only
- R1 + prior-only
- R1 + R1-adapted PriorG

本问题用于判断：
PriorG是仅对V4有效的模型特定参数，
还是一种能够通过重新适配迁移到不同Judge的轻量决策方法。

==================================================
三、R1专属PriorG：监督范围必须严格对齐历史V4
==================================================

不要新设计训练集。

找到历史T-S PriorG所用的同一批051校准材料：
- 同16名患者
- 同T-S scoring有效ID
- 历史计数约为48 / 47 / 48，共143条
- 精确ID以仓库冻结工件为准，不以本提示词数字代替真实工件

这些校准ID必须：
1. 使用与当前主B配置对应的相同claim + C48；
2. 调用R1 scoring一次；
3. 保存R1原生verdict和三类label_scores；
4. 使用与历史PriorG完全相同的G目标函数、正则、参数范围、
   log-score变换及优化配方重新拟合R1的G参数；
5. prior reference counts和calibration counts使用历史同定义；
6. 不使用本轮评价面板GT调参数。

优先复用：
- tasks/052_first_tier_validation/fit_calibration052.py
- tasks/053_thinking_prior_validation/common053.py
- 现有PriorG定义和冻结工件

不要发明PriorG-v2。

必须输出：
- V4原Frozen G参数
- 新R1 fitted G参数
- reference prior counts
- calibration counts
- 训练ID SHA/hash
- 损失、收敛状态
- 参数是否命中边界

==================================================
四、评价样本
==================================================

不要使用085原180条作为主评价面板。

从095固定母体中建立新的评价材料。

首先排除：
- 上述R1 PriorG校准患者/校准ID；
- 无法构造完整B请求的记录；
- 缺Original VeriFact发布结果的记录；
- 缺可复用V4-B raw结果的记录；
- 其他使三方无法同ID比较的记录。

严禁根据：
- Original是否正确
- V4是否正确
- 085表现
- 历史error category
- PriorG是否翻转
来选择自然面板。

------------------------------
A. Natural panel
------------------------------

目标N=800。

在合格母体中按：
GT × author_type
做比例分层，目标比例等于排除后的合格母体真实比例。

层内：
固定SHA256规则排序取样。

这不是balanced benchmark，而是保持自然分布的固定评价面板。

记录：
- 每类GT数
- human/llm数
- 患者数
- 各患者claim数
- 与完整合格母体的分布差异

主PA/MCC/Macro-F1等总体结论只来自Natural panel。

------------------------------
B. Minority diagnostic panel
------------------------------

目标N=200，与Natural panel不重叠：
- NS 100
- NA 100

在类别内尽量保持author_type和患者覆盖合理，
仍按固定hash取样，不按模型历史结果取样。

这个面板只用于：
- NS/NA recall
- false-S
- 转移类型
- error diagnosis

不得把它和Natural panel合并计算“总体PA”。

==================================================
五、并行性能测试：必须先做，且测试请求计入正式实验
==================================================

用户不能接受7–11小时串行运行。

必须实现一个新的异步/并行runner，
但请求body、parser、receipt、retry/resume语义继续沿用085。

要求：
- Python asyncio + bounded semaphore，或等价安全实现
- 每个request_id唯一
- HTTP200成功位置永不重发
- 单请求原始response和receipt立即落盘
- 支持Ctrl+C后resume
- 并发改变不得改变request body
- 不允许在并发测试中对同一个ID重复推理

并发测试使用已经冻结的正式Natural panel中的不同ID。
这些成功回答直接纳入最终实验，不浪费调用。

在读取评价GT结果之前完成并发档位选择。

------------------------------
Stage P0：协议预检
------------------------------

从Natural panel固定选1条短输入。

concurrency=1

必须验证：
- HTTP200
- model字段正确
- reasoning_content可解析
- final content非空
- 085 parser可得到合法verdict
- scoring parser可得到三类label_scores
- finish_reason不是length
- usage存在
- 总context不超20K

如果失败：
停止正式实验，只修协议兼容问题。
不得读取性能结果决定prompt修改。

------------------------------
Stage P1-P4：吞吐benchmark
------------------------------

从Natural panel按冻结输入长度分布提前构造互不重叠的小批次。
尽量使每个batch都包含short/medium/long请求。

依次测试：

P1: concurrency=2，至少8条
P2: concurrency=4，至少12条
P3: concurrency=8，至少16条

若P3稳定，再测试：
P4: concurrency=12，至少24条

只有当P4仍有明显吞吐增益且无异常时，才允许额外测试：
P5: concurrency=16，至少24条

不得继续无上限增大并发。

每个stage记录：
- requests
- success / failure
- core parse valid
- wall-clock seconds
- requests/min
- aggregate prompt tokens
- aggregate completion tokens
- tokens/sec（若usage可得）
- median / P90 / max request latency
- finish_reason分布
- completion token median/P90/max
- timeout数
- 429/500/503等
- server是否重启
- 是否OOM
- 测试前后服务健康状态

并查看服务器是否仍响应/v1/models。
如能通过现有方式读取vLLM metrics，可记录，但不是硬要求。

------------------------------
并发档位选择
------------------------------

选“最高稳定吞吐档”，而不是单纯最高concurrency。

稳定要求：
- 没有OOM
- 没有服务重启
- HTTP成功率100%，或仅有明确可恢复通信失败且重试后成功
- core parse有效率至少与085兼容水平一致
- 不出现明显新增finish_reason=length
- P90 latency没有出现失控增长
- 相比前一稳定档吞吐有实际增益

如果concurrency=12相对8吞吐提升<10%，优先选8。
如果16相对12提升<10%，优先选12。

不要为了几%的吞吐冒OOM/不稳定风险。

==================================================
六、正式规模按“速度”决定，不按性能决定
==================================================

在并发benchmark结束后、读取模型准确率结果之前，
根据实测吞吐估算剩余R1墙钟。

总调用包括：
- 143左右R1 calibration
- Natural panel
- Minority diagnostic panel
减去并发测试中已经完成的正式ID

预先定义三个规模档位：

Tier A：
- calibration全部
- Natural 800
- diagnostic 200

若预计剩余R1正式推理墙钟 <= 3.5小时：
使用Tier A。

Tier B：
- calibration全部
- Natural 600
- diagnostic 120（NS60 + NA60）

若Tier A预计 >3.5小时，
但Tier B预计 <=3.5小时：
使用Tier B。

Tier C：
- calibration全部
- Natural 400
- diagnostic 100（NS50 + NA50）

若Tier B仍预计 >3.5小时：
使用Tier C。

如果Tier C预计仍超过4小时：
不要自动开始大批量正式推理。
输出：
R1_RUNTIME_TOO_HIGH
以及：
- 各并发档吞吐
- 三个Tier预计墙钟
- 已完成请求数
然后等用户决定。

档位选择只允许依据：
- 实测速度
- 剩余请求量
- 用户时间限制

绝不能根据谁表现好/差调整规模。

一旦选定Tier，冻结其ID/hash并写freeze文件，
之后不得改变。

==================================================
七、正式R1运行
==================================================

顺序建议：

1. 完成全部R1 PriorG calibration请求；
2. 完成冻结Natural panel；
3. 完成冻结Minority diagnostic panel。

可以按最优并发档持续执行。

每隔固定数量（如25或50条）：
- flush receipts
- 更新completion manifest
- 检查/v1/models
- 检查失败/timeout/OOM状态
- 打印完成数、剩余数、实测requests/min、预计剩余时间

不要每条打印大段reasoning。

所有HTTP200成功位置只执行一次。
通信失败按085已有安全规则处理。
不要因为模型输出标签/理由“不满意”而重跑。

若单个请求finish_reason=length：
保存原结果，不自动重跑；
最后统一列为core-invalid或按冻结parser规则处理。

==================================================
八、R1推理结束后的关键通知
==================================================

一旦所有本轮R1请求完整落盘并完成reconciliation，
立即输出一条非常醒目的：

R1_INFERENCE_DONE

同时打印：
- 完成R1请求数
- calibration / natural / diagnostic各多少
- HTTP200数
- core-valid数
- 总墙钟
- 最终并发数
- requests/min
- 总prompt/completion tokens
- response目录
- reconciliation文件

然后提醒用户：
“现在可以关闭AutoDL实例，后续PriorG拟合、统计和报告全部离线完成。”

不要为了生成表格、bootstrap或写报告继续占用GPU。

==================================================
九、离线评价
==================================================

GPU关闭后再读取GT并完成统计。

Natural panel至少生成一张统一大表：

方法：
1. Original VeriFact published
2. V4-B raw
3. R1-B raw
4. R1-B + V4 Frozen PriorG
5. R1-B + R1-adapted PriorG
6. 当前V4-B + Frozen PriorG（作为最终系统参照，可复用已有预测）

列：
- correct / N
- PA
- MCC
- AC1
- Macro-F1
- S Recall
- NS Recall
- NA Recall
- false-S
- false-S rate

每列最优值可在论文表版本中标识，
但分析文本不能只挑有利指标。

另做PriorG机制表：

- R1 raw
- R1 U0
- R1 prior-only
- R1 fitted-G-only
- R1 + V4 Frozen PriorG
- R1 + R1-adapted PriorG

输出逐例transition：
- rescue
- harm
- wrong→wrong
- class transition
- GT分层

对重要比较做patient-cluster bootstrap：
- R1 raw vs Original
- V4 raw vs Original
- R1 raw vs V4 raw
- R1-adapted PriorG vs R1 raw
- R1-adapted PriorG vs V4-Frozen-PriorG-on-R1
- R1-adapted PriorG vs Original
- 如有必要，R1-adapted vs 当前V4最终系统

报告：
ΔPA和ΔMCC的95%患者cluster bootstrap区间。

同时分：
- human
- llm

但分层只是描述，不强行宣称小样本显著。

==================================================
十、Original VeriFact + V4 可选桥接
==================================================

这不是主任务阻塞项。

先离线检查现有仓库材料是否已经能够低成本构造：
“原VeriFact发布reference / 原命题 + V4 Judge”的合法桥接。

如果历史018/078等已经有足够可复用结果，
优先复用，不重新API调用。

如果只需少量DeepSeek V4调用且不需要：
- 新Qdrant
- 新embedding/rerank服务
- 新GPU
- 新辅助模型部署
则可以冻结一个120–160条的小桥接面板。

目标回答：
把Original evidence/reference交给现代V4后，
与C48 + V4 raw之间还有多少差异？

必须准确命名：
“published-reference + V4 bridge”
或实际对应的实现。

除非确实完整复现原VeriFact Judge链，
否则不能写成“Original VeriFact full pipeline + V4”。

如果实现不方便或新增成本明显，
记录为NOT_RUN_WITH_REASON，
不影响R1主实验结项。

==================================================
十一、报告必须回答的问题
==================================================

报告不是简单说谁最好，要明确回答：

1. 在更合理的新自然面板上，
   R1 raw、V4 raw、Original VeriFact各处在什么位置？

2. 095中V4 raw PA较低、MCC/false-S较好的风险结构，
   在本新面板是否仍存在？

3. 085里R1的S偏向/NA弱点是否在新面板继续出现？

4. V4 Frozen PriorG直接套R1有没有用？

5. 同配方重新适配R1以后：
   - PA改变多少？
   - MCC改变多少？
   - Macro-F1改变多少？
   - false-S改变多少？
   - S/NS/NA recall怎么变？

6. R1-adapted PriorG的增量主要来自：
   - fitted G
   - prior adjustment
   - 两者组合
   哪一个？

7. 能否支持：
   “PriorG配方具有跨Judge可重新适配性”
   还是只能支持：
   “R1上重新拟合后在本面板有改善”
   或者根本不支持迁移？

不要超过实验本身能证明的范围。

==================================================
十二、工件
==================================================

新任务编号可使用当前零API准备已经创建的编号/目录；
不要因为本提示词另建冲突编号。

至少产出：

- protocol / freeze
- endpoint/service manifest
- exact calibration IDs
- natural sample freeze
- diagnostic sample freeze
- concurrency benchmark.json/csv/md
- request ledger
- response reconciliation
- R1 parsed predictions
- R1 calibration model
- PriorG component ablation
- unified same-ID predictions
- main metrics
- paired bootstrap
- author subgroup
- class transitions
- cost/runtime ledger
- report.md
- selfcheck
- history_difference / manuscript implications

更新项目状态时，
不要覆盖095结论；
将本任务作为“跨Judge公平性与PriorG迁移验证”。

==================================================
十三、现在立即执行
==================================================

先：
1. 检查零API准备工件是否完整；
2. GET /v1/models；
3. 运行P0；
4. 运行P1/P2/P3；
5. 稳定时再P4，必要时P5；
6. 在读取评价性能之前选择并发和Tier；
7. 冻结；
8. 开始正式R1推理。

如果P0或并行稳定性失败，不进入正式批量。

不要再等待用户逐条确认正常技术步骤。
只有出现以下情况才暂停询问：
- endpoint不可达
- 模型身份不符
- parser无法兼容且需要改变prompt语义
- Tier C仍预测>4小时
- GPU/OOM/服务持续崩溃
- 需要扩大用户未授权的云API/GPU成本范围