继续当前 research-verifact 项目。

我刚才人工中断了你上一轮执行，因为旧R1服务速度异常。
现在AutoDL上的R1服务已经重新启动。

请先完整理解下面的状态迁移，不要直接resume旧runner。

==================================================
一、状态变化
==================================================

上一轮使用的R1服务为：

模型：
Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ

vLLM：
0.10.1.1

dtype：
float16

max_model_len：
20000

但是服务启动时显式使用了：

--quantization awq

vLLM日志明确提示该模型可以使用awq_marlin，
而强制普通awq可能明显较慢。

上一轮P0：
- HTTP200
- reasoning正常
- final content正常
- 三分类/三分数解析通过
- 无context overflow
- 无finish_reason=length
- 但单条延迟约378秒

这与085历史同模型正式运行的约25秒中位请求时长差异过大。

之后曾启动concurrency=2的P1，
但用户在其执行过程中人工中断Codex。
因此本地可能存在：
- P0完整旧AWQ HTTP200
- P1部分或全部旧AWQ HTTP200
- 未完成attempt
- interruption产生的unknown outcome

这些都必须先盘点，但不要删除。

==================================================
二、当前新的R1服务
==================================================

现在服务已改为：

模型：
Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ

vLLM：
0.10.1.1

量化权重：
仍然是同一份ModelScope AWQ模型

推理kernel：
--quantization awq_marlin

dtype：
half / float16

max_model_len：
20000

reasoning parser：
deepseek_r1

temperature：
0

top_p：
1

正式max_tokens：
8192

服务仍通过本地SSH tunnel访问：

R1_BASE_URL=http://127.0.0.1:18000/v1
R1_MODEL=Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ
R1_API_KEY=EMPTY

首先检查：

GET http://127.0.0.1:18000/v1/models

必须确认：
- 精确模型名匹配
- max_model_len=20000

否则停止并报告。

==================================================
三、旧AWQ结果的处理原则
==================================================

非常重要：

旧普通AWQ backend产生的所有P0/P1结果：

- 不删除；
- 保留原request/response/receipt/hash；
- 标记为：
  AWQ_DIAGNOSTIC_ONLY
- 只能用于部署性能诊断；
- 不允许进入最终R1 raw性能评价；
- 不允许进入R1 PriorG拟合；
- 不允许与新AWQ-Marlin结果混在同一正式预测列中。

旧P0/P1即使HTTP200且parser有效，
也不能因为“成功请求不重发”规则而阻止新backend重新运行相同proposition。

原因：
正式评价必须统一来自同一个backend profile。

==================================================
四、必须建立新的backend namespace
==================================================

不要修改历史085工件。

也不要覆盖上一轮旧AWQ诊断工件。

为当前新backend建立独立身份，例如：

backend_id =
valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k

或者当前任务目录中等价的明确命名。

新的request_id / cache key必须包含backend_id
或等价backend hash。

也就是说：

同一个 proposition
+ 完全相同 request body
+ 不同 backend profile

必须能够各自保存一份独立回答。

不能因为旧AWQ目录存在HTTP200就跳过AWQ-Marlin调用。

同时保存新backend manifest，至少包括：

- model served name
- model source/本地身份记录
- vLLM 0.10.1.1
- quantization=awq_marlin
- dtype=float16
- max_model_len=20000
- reasoning_parser=deepseek_r1
- temperature=0
- top_p=1
- max_tokens=8192
- endpoint
- created time
- 与旧AWQ backend的区别

==================================================
五、不要重新抽样
==================================================

上一轮已经冻结的研究设计继续沿用。

已知：
- 合格母体约7484条
- 84名患者
- calibration使用历史T-S PriorG对应的同一监督范围
- Natural panel使用800/600/400嵌套设计
- diagnostic panel已准备
- 缺V4 raw等不能同ID比较的记录已经排除
- 所有正式请求加8192输出预算后均能放入20K上下文

不要因为服务重启：
- 重抽Natural panel
- 改hash规则
- 改GT比例
- 改患者
- 改calibration监督范围

如果上一轮freeze已经生成并通过自检，
继续使用同一freeze。

只更新backend身份和正式response来源。

==================================================
六、先盘点中断状态
==================================================

正式发新请求前：

1. 列出旧AWQ：
   - P0成功数
   - P1已成功HTTP200数
   - incomplete attempts
   - unknown outcome数
   - 已保存response数

2. 对可能处于unknown outcome的旧AWQ请求：
   - 不需要为了正式实验补跑；
   - 保留并标记旧backend诊断未完成即可。

3. 不读取旧P0/P1的GT准确率结果。

4. 生成一个backend_transition.md/json：
   old_backend = awq
   new_backend = awq_marlin
   reason = runtime-only performance diagnosis before formal evaluation
   performance_GT_read_before_switch = false
   sample_freeze_changed = false

==================================================
七、新AWQ-Marlin速度测试
==================================================

现在重新从AWQ-Marlin开始性能测试。

这些测试使用已冻结Natural panel中的正式ID。
如果最终选择AWQ-Marlin作为正式backend，
这些新AWQ-Marlin成功结果可以直接计入最终评价。

但是在完成并发选择之前：
禁止读取或计算GT准确率。

------------------------------
M0：单请求协议+速度检查
------------------------------

固定选Natural panel中的1条，
最好使用上一轮P0同一个proposition，
这样可做部署速度对照。

concurrency=1。

检查：
- HTTP200
- model正确
- final content非空
- reasoning_content非空
- 三分类合法
- 三label_scores合法
- finish_reason != length
- usage存在
- context <= 20000

记录：
- prompt_tokens
- completion_tokens
- reasoning长度
- wall latency
- completion_tokens / second

如果M0仍然 > 180秒：
先不要自动开始大规模benchmark。
输出：
AWQ_MARLIN_SINGLE_TOO_SLOW
并报告旧AWQ与AWQ-Marlin速度，
等待用户决定。

如果M0明显恢复正常，
继续下面测试。

------------------------------
M1：concurrency=2
------------------------------

使用4个不同正式Natural ID。

记录：
- 总wall time
- requests/min
- aggregate completion tokens/sec
- 每条latency
- prompt/completion tokens
- median / max latency
- parse valid
- finish reasons
- HTTP错误

------------------------------
M2：concurrency=4
------------------------------

使用8个不同正式Natural ID。

同样记录全部吞吐指标。

------------------------------
M3：concurrency=8
------------------------------

如果M2：
- 无OOM
- 无service restart
- 无持续HTTP错误
- parser正常
- 无明显新增length truncation

则使用12个不同正式Natural ID测试concurrency=8。

------------------------------
M4：concurrency=12（可选）
------------------------------

只有concurrency=8稳定，
并且GPU服务正常，
且有理由认为吞吐还能提升时，
再用16个不同Natural ID测试12并发。

暂时不要测试16并发，
除非12并发相比8并发仍有 >=15% 的实际requests/min增益，
并且没有明显P90 latency恶化。

==================================================
八、并发选择规则
==================================================

选择“稳定情况下总吞吐最高”的档位，
不是单纯最大concurrency。

主要指标：

1. requests/min
2. aggregate completion tokens/sec
3. HTTP成功率
4. core parse valid率
5. P90 latency
6. OOM / restart / timeout
7. finish_reason=length

如果：

concurrency=8 相比4
吞吐提升 <10%

则优先4。

如果：

concurrency=12 相比8
吞吐提升 <10%

则优先8。

不要为微小吞吐收益换明显不稳定。

==================================================
九、与085做运行速度对照
==================================================

明确引用仓库085历史运行事实：

085 Valdemardi正式实验：
- client_concurrency=1
- median request ≈25.289 s
- longest request ≈41.984 s
- 360 HTTP200
- retries=0

当前AWQ-Marlin不要求精确复现这些数值，
因为当前样本、输出长度可能不同。

但必须报告：

- 旧AWQ P0 ≈378秒
- 新AWQ-Marlin M0延迟
- 当前各并发吞吐
- 当前completion token长度

用于确认部署速度是否恢复到合理范围。

不要把速度差异解释成模型能力差异。

==================================================
十、根据新实测速率重新决定实验规模
==================================================

仅在完成AWQ-Marlin benchmark后，
且在读取GT性能前，
根据实测吞吐决定Tier。

原计划仍为：

Tier A：
- calibration全部
- Natural 800
- diagnostic 200

Tier B：
- calibration全部
- Natural 600
- diagnostic 120

Tier C：
- calibration全部
- Natural 400
- diagnostic 100

但不要机械使用旧AWQ速度预测。

必须用AWQ-Marlin实际requests/min重新计算。

规则：

若Tier A预计新增R1墙钟 <=3.5小时：
选Tier A。

否则若Tier B <=3.5小时：
选Tier B。

否则若Tier C <=4小时：
选Tier C。

若Tier C仍 >4小时：
停止并输出：

R1_RUNTIME_TOO_HIGH

然后等待用户。

Tier选择不能依据准确率结果。

==================================================
十一、正式实验范围保持不变
==================================================

如果速度通过，则继续原研究计划：

A. R1 calibration
- 使用历史T-S PriorG相同监督范围
- 相同ID
- 相同16患者
- 相同PriorG配方
- 不使用评价面板GT

B. Natural panel
比较：
1. Original VeriFact published
2. V4-B raw
3. R1-B raw
4. R1-B + V4 Frozen PriorG
5. R1-B + R1-adapted PriorG
6. 当前V4-B + Frozen PriorG

C. R1 PriorG机制
比较：
- raw
- U0
- prior-only
- R1 fitted-G-only
- V4 Frozen PriorG on R1
- R1-adapted PriorG

D. Minority diagnostic
NS/NA单独分析，
不与Natural panel合并算总体PA。

==================================================
十二、PriorG适配规则不变
==================================================

不要改PriorG方法。

R1-adapted PriorG必须继续使用：

- 与历史T-S相同监督ID/患者
- 相同score→logscore处理
- 相同G参数化
- 相同NLL目标
- 相同正则
- 相同参数范围
- 相同prior adjustment定义
- 相同reference/calibration counts来源

只允许模型输出分数改变，
因此重新得到R1自己的G参数。

不得：
- 搜lambda
- 改损失
- 改训练患者
- 改prior
- 根据Natural结果再优化

==================================================
十三、成功请求和恢复规则
==================================================

对于“当前AWQ-Marlin backend内部”：

HTTP200成功位置永久保存，
不得重复调用。

runner必须支持：
- interruption safe
- resume
- atomic receipt
- unique request id
- backend-aware cache
- Ctrl+C恢复

旧AWQ成功不算AWQ-Marlin成功。

新AWQ-Marlin内部成功则不能重复。

==================================================
十四、R1完成后立即通知用户关AutoDL
==================================================

完成所有选定R1请求、
保存response、
完成reconciliation之后，

立即输出：

R1_INFERENCE_DONE

并报告：
- backend=AWQ-Marlin
- Tier
- calibration数量
- Natural数量
- diagnostic数量
- HTTP200
- core valid
- wall time
- final concurrency
- requests/min
- prompt tokens
- completion tokens
- response目录
- reconciliation文件

然后明确告诉用户：

现在可以关闭AutoDL实例。

不要为了：
- PriorG拟合
- GT评价
- bootstrap
- 写报告
继续占用GPU。

这些全部离线CPU完成。

==================================================
十五、现在立即执行的顺序
==================================================

现在从这里接续：

1. 检查/v1/models；
2. 盘点旧AWQ中断工件；
3. 建立backend_transition记录；
4. 建立新的AWQ-Marlin backend namespace；
5. M0；
6. 若M0速度合理，M1；
7. M2；
8. 必要时M3/M4；
9. 根据速度冻结Tier；
10. 正式推理；
11. reconciliation；
12. 输出R1_INFERENCE_DONE；
13. 等用户关GPU；
14. 再离线做PriorG拟合与全部统计。

正常技术步骤不需要再次逐项询问用户。

仅以下情况暂停：
- endpoint不可达
- 模型身份不符
- AWQ-Marlin M0仍>180秒
- parser无法兼容
- GPU OOM/服务持续崩溃
- Tier C预计仍>4小时
- 需要扩大未授权费用或研究范围