# 004_event_alignment_pilot

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/004_event_alignment_pilot/README.md)。 独立结论查[审计末尾](../../reviews/004_event_alignment_pilot.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

状态：**已完成，修订定向独立复核 PASS，可正式冻结／结项（2026-09-14）。** 原真实执行审计的重放阻塞项及费用归属问题均已关闭，见 [独立复核结论](../../reviews/004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14)。执行者修订与自查保留在 [历史修订说明](../../outputs/004_event_alignment_pilot/verification_live/run_002/README.md)。实际服务为硅基流动（SiliconFlow），Judge 为 `deepseek-ai/DeepSeek-V4-Flash`；AWS Bedrock / Groq 已放弃，不再是当前待办。运行前登记见 [live_protocol.md](live_protocol.md)，真实实验为 `outputs/004_event_alignment_pilot/run_003`。历史 run、回执及 manifest 保持不变。旧授权仅适用于当时的调用，本任务的历史结果保持冻结。今后交办任务的收费调用按 [当前 API 费用规则](../../AGENTS.md#api-调用费用与确认规则)：任务预估总费用不超过 40 元可直接执行，超过则先确认。

## 问题与设计

验证 003 的 H1：显式核对事件、时间、状态和证据支持范围，是否比常规判断及普通结构化解释更准确。固定现有 proposition、医生 GT 和检索结果，不新增检索、不重切分、不训练、不补医生标签。

下表为冻结的预设要求；实际检查结构遵守有限，不能将要求视为全部响应都已遵守。

| 臂 | 判断方式 | 预设输出与预算 |
| --- | --- | --- |
| `routine` | 常规直接判断，自由解释 | JSON verdict/reason，checks 为空 |
| `structured` | 普通结构化解释：命题概括、相关证据、支持情况、反对情况、整体判断 | 五项 checks + verdict/reason |
| `event_alignment` | 事件、时间、状态、范围、支持充分性 | 五项 checks + verdict/reason |

三臂共用标签定义、同一实际 Judge、同一完整 reference、一次生成、相同解码参数和输出上限，不使用第二个格式修复模型。每条独立会话，不将其他臂的回答加入历史。每条命题的调用次序采用确定性平衡排列，以减少固定调用顺序影响。

解释总上限均为 200 个英文词，服务输出上限为 2,048 tokens、temperature=0；三臂参数已在真实 run_003 统一绑定并冻结。普通结构化/事件臂的方法指令分别为 142/145 个词，具有相同的五项输出结构；两者请求仅相差 33 个字符。相同上限不保证实际计算量相同，须报告真实 input/output/reasoning token 和延迟。若事件臂明显使用更多生成或隐藏推理预算，其收益不能单独归因于对齐机制；必要时作为下一次有记录的开发迭代匹配预算，不能事后筛掉高预算样本。

本轮已明确关闭 thinking（enable_thinking=false），seed 未设置，不声称 temperature=0 保证可重复。具体文本见 [common](prompts/common.md)、[routine](prompts/routine.md)、[structured](prompts/structured.md)、[event_alignment](prompts/event_alignment.md)，离线参数见 [config.json](config.json)，本轮服务参数见 [siliconflow_config.json](siliconflow_config.json)。

## 已冻结的样本与证据

使用 003 的原 [患者分组](../../outputs/003_error_analysis/patient_groups.json)，不重抽。按 `SHA256("003_error_analysis/patient-split/v1:" + canonical_subject_id)` 排序开发组，取前 6 名：**93147、29426、85689、91315、45979、98790**。原 JSON 的展示顺序是患者编号顺序，不能直接取其前六项。

| 作者 | 有效 atomic claims | Supported | Not Supported | Not Addressed |
| --- | ---: | ---: | ---: | ---: |
| LLM-written | 181 | 166 | 7 | 8 |
| Human-written | 240 | 161 | 24 | 55 |

共 421 条命题、1,263 个计划请求；排除 1 条 LLM invalid，保存其 ID。包含患者 98790 的 77 条时间冲突标记命题（LLM 29、human 48），主分析保留原值，敏感性分析在所有臂共同排除这 77 条。无第二轮标注流程异常行。其余开发患者和保留测试患者不进入模型输入或评价。

证据固定为 release `v1.1.0-rater-121` 的真实 payload：R1-70B、sentence facts N100、rerank、absolute_time、current admission、deduplicate=True。421 条均有对应发布预测及完整 payload，逐字保留 reference、日期和编号；实得证据块数为 80–100，不按名义 N 补齐。只从官方文件提取所需行并核对与 002 的文件指纹及键，不重新做全面审计或检索。

模型消息只有命题和原 reference。患者/住院/作者标识用于本地索引；GT、医生票数、旧 verdict/reason、BHC/parent 均不进入消息。reference 是模型实际输入，不是医生 gold evidence。

**证据来源模型与新实验 Judge 分开记录。** 原 release R1-70B 的权重名为 `casperhansen/deepseek-r1-distill-llama-70b-awq`，还用了另一个模型转换结构化输出。本实验仅一次生成、由同一模型直接输出 JSON，不声称复现作者推理管线。本轮三臂均由硅基流动 DeepSeek-V4-Flash 重新生成，不能把发布的 R1 标签当成本轮 routine 对照。模型别名由服务返回核对，但供应商没有提供可冻结的不可变权重修订号。

## 固定评价与判读

- 共用 002 `verifact_research.evaluation.evaluate` / `paired_compare`，不另写指标。主分析 valid-only，完整队列，三分类 micro PA/AC1/MCC，1,000 次患者 bootstrap；LLM/human 分开。
- 主要对比：`event_alignment − structured` 的 MCC；辅助对比：`event_alignment − routine`、`structured − routine`。同时看各类 precision/recall/F1、非 S→S、S→非 S、NS↔NA、正确变错/错误改正计数与逐患者结果。
- 时间冲突排除是预设敏感性分析，主结果始终保留完整 421 条。所有臂使用同一实际分母与排除 ID。
- 若只优于 routine、未优于 structured，不能说明事件核对具有额外价值；若全面变严造成 S 召回下降，不能只挑错误减少作结论；若实际预算失衡，应保留该限制。
- 6 名开发患者的结果仅决定是否值得扩大开发验证，不作为显著性或最终测试结论。LLM 只有 7 条 NS、8 条 NA，单例影响很大。后续若扩大，只沿既定开发哈希顺序，不按成绩重新选患者；保留测试组仍不使用。

## 历史离线准备与文件

以下命令用于重建离线准备或纯虚构软件演练，已有正式结果无需重新准备。日常真实结果重放见下一节。在项目根目录、Conda `research-verifact` 环境中运行：

```powershell
python -B tasks/004_event_alignment_pilot/pilot.py prepare
python -B tasks/004_event_alignment_pilot/pilot.py synthetic
python -B -m unittest discover -s tests -p test_event_alignment_pilot.py -v
```

`prepare` 新建一个 `outputs/004_event_alignment_pilot/run_XXX/`；`synthetic` 新建 `outputs/004_event_alignment_pilot/synthetic/run_XXX/`，只使用手写虚构 fixture 和预写响应。这些命令不联网、没有模型推理，不覆盖旧运行。新任务没有新增依赖。

离线准备阶段的历史复查：两次准备的 16 个文件逐字节一致，当时全项目 54 项测试通过（新增 12 项）。检查记录见 [verification_001](../../outputs/004_event_alignment_pilot/verification_001/verification.json)；已有任务的历史文件保持原样。

| 文件 | 用途 |
| --- | --- |
| `pilot.py` | 局部准备、消息构造、响应校验、共用评价及虚构演练；不包含推理服务实现 |
| `config.json`、`prompts/` | 实验设计与提示词，准备时保存快照 |
| `fixtures/synthetic.json` | 6 名虚构患者、两种作者共 12 条命题的软件 fixture |
| `run_XXX/cohort_llm.csv`、`cohort_human.csv` | 全部实际评价 ID、GT、患者、住院与既有异常标记 |
| `run_XXX/inputs.jsonl` | 每条命题和完整 reference，共享给三臂，无 GT 字段 |
| `run_XXX/request_schedule.csv` | 1,263 次计划调用的固定顺序、原文/消息哈希与字符长度 |
| `run_XXX/historical_predictions_*.csv` | 原作者发布预测，单列历史参照，不替代新 routine |
| `run_XXX/excluded_invalid.csv`、`selected_patients.csv` | 排除 ID、实际患者和排序哈希 |
| `run_XXX/summary.json`、`report.md`、`provenance.json`、`manifest.json` | 规模、准备状态、来源和文件/代码指纹 |

消息由 `make_request(item, arm, config, prompts)` 确定生成；消息、Judge 配置及生成配置共同计算 request SHA-256。这是供应商无关的逻辑请求哈希；真实适配器另存 `api_body_sha256`，并保存完整原生请求、响应、供应商模型标识、usage、stop reason、时间和费用估算，不能混同两种哈希。

本地响应解析入口：

```powershell
python -B tasks/004_event_alignment_pilot/pilot.py score --bundle outputs/004_event_alignment_pilot/synthetic/run_001/bundle --responses outputs/004_event_alignment_pilot/synthetic/run_001/mock_responses.jsonl
```

响应 JSONL 每行含 `request_id`、`request_sha256`、`judge`、`status`、`finish_reason`、`output_text`、`usage`；示例见上述纯虚构文件。`output_text` 是最终 JSON 文本；usage 的 `output_tokens` 需包含 `reasoning_tokens`，不能把未知推理 token 静默记 0。本轮 SiliconFlow 适配器已按原生 usage 字段标准化，原生字段继续保留；更换服务时须重新核实计量定义。

上述离线 `pilot.py score` 保留最初严格行为，不改写旧 run。本轮真实分析走 `analyze_live.py`：未知/重复/缺失响应、非法标签/JSON、截断、模型不符或无有效 usage 阻止完整评价；对唯一合法标签，检查项/证据编号/200 词偏离单列诊断，原标签保留计分。该差异在任何真实调用前已登记并冻结，见 [运行前协议](live_protocol.md)。引用校验只证明编号存在，不证明医学引用正确；不能删掉偏离样本后宣称完整分母。

## 真实服务运行与复查

实际服务参数见 [siliconflow_config.json](siliconflow_config.json)，模型适配见 [siliconflow.py](siliconflow.py)，冻结/断点续跑见 [live.py](live.py)，原始回执重放及 002 统一评价见 [analyze_live.py](analyze_live.py)。全部使用已有依赖和 Python 标准库，环境定义无需新增包。

```powershell
# 只读取本地原始响应，不调用 API；输出位置必须尚不存在。
python -B tasks/004_event_alignment_pilot/analyze_live.py --run outputs/004_event_alignment_pilot/run_003 --output outputs/004_event_alignment_pilot/replay_local --no-report
# 新建 verification 目录，禁用网络连接后运行测试和完整重放。
python -B tasks/004_event_alignment_pilot/verify_live.py --run outputs/004_event_alignment_pilot/run_003
```

真实首轮由 `live.py run` 执行；本轮遇到余额不足后补充 [resume_balance.py](resume_balance.py)，当时用它完成补跑；当前不再续跑或补生成失败项。它校验冻结代码和输入指纹，仅将明确的无答案 402/code 30001 列为充值后可恢复服务错误，单独登记 `balance_recovery.json` 并保留所有旧回执。再次运行复用已有答案，仅补未完成服务请求。发现新的余额错误会停止尚未发送的工作（已在途请求可完成）。最多 5 次同请求服务尝试，所有成功/失败及未知结果均保留；不得删除回执来重跑。崩溃后若有 runner.lock，应核实其中 PID 已退出后才移除锁文件。逐臂/配对主评价要求原完整分母，无 available-case。本轮 LLM routine 的一条回答在 2,048 tokens 截断，保留为失败且不再生成，相应比较不评分；structured 与 event_alignment 全部完整，两种作者分别用 181/240 条评价。原离线整体汇总器的全三臂阻止规则未修改，真实分析另用同一 002 评价按完整配对计算，并在 analysis_scope.json 明确记录此项看到失败后才添加的处理。

| 真实 run 文件 | 用途 |
| --- | --- |
| `manifest.json`、`preflight.json`、`config.json` | 调用前冻结时间、代码/输入哈希、授权依据、服务参数、预算和预检限制 |
| `requests.jsonl.gz`、`request_schedule.csv` | 全部逻辑与原生请求、固定顺序及独立哈希；不保存 Authorization header |
| `balance_recovery.json` | 余额中断后的恢复登记、540 个无答案请求及旧失败回执指纹；不修改原冻结配置或已有答案 |
| `attempt_starts.jsonl`、`receipts/*.json` | 每次开始记录、完整原生响应、trace ID、usage、原始 JSON 文本、归一化诊断与费用估算 |
| `analysis/report.md` | 唯一用户主报告，执行结果与研究判读 |
| `analysis/predictions_*.csv`、`metrics.json`、`contrasts.csv` | 002 完整队列评分、三组对比与 1,000 次患者 bootstrap |
| `analysis/robustness.json`、`changed_predictions.csv` | 留一患者分析与可回查的标签变化 ID；不是新增医学 GT |
| `analysis/adherence.json`、`adherence_by_response.csv` | 检查项数量/名称/词数遵守诊断；不按遵守情况过滤评价样本 |
| `analysis/usage.json`、`attempts.csv` | 三臂实际 token、缓存、解释长度、延迟、调用和费用；费用并非已核对账单 |
| `analysis/response_checks.json`、`manifest.json` | 从原始回执重放校验、源文件与分析产物指纹 |

密钥仅由本地环境或已有 .env 的同名变量读入内存，不写入产物。官方价格公告与模型目录不一致，两种估算单列；服务模型别名不能保证将来底层权重不变。没有取得逐请求精确 tokenizer 预检，改为字节余量筛查、超长虚构调用和每次响应的实际 usage 核对；不能把这一限制写成精确离线计数已完成。

本轮主对比 ΔMCC：LLM +0.0425，human -0.0416，两个患者 bootstrap 区间均跨 0；事件臂 NA/S 类别代价和检查结构遵守问题详见唯一 [中文主报告](../../outputs/004_event_alignment_pilot/run_003/analysis/report.md)。当前不建议直接扩大该版本。真实推理按 usage 和公开日期价格估算约 ¥30.326，虚构测试另约 ¥0.1744；用户反馈本轮消耗约 30 元额度，未逐笔核对账单。后续实验需先明确 token／调用预算和费用上限，最终论文方法与贡献点仍未确定。

执行自查入口为 `python -B tasks/004_event_alignment_pilot/verify_live.py --run outputs/004_event_alignment_pilot/run_003`，重评分、测试和密钥排查均不新增 API 调用。独立审计文档由独立审计模型维护，执行者不改其结论或宣布 PASS。

## 2026-09-14 离线修订

`analyze_live.py` 将 preflight 中的工作区保护文件作为运行时快照，当前文档或编辑器配置的变化/缺失仅写入 `response_checks.json`，不阻止重评分。`live.load_jobs` 仍严格检查冻结输入、提示词、配置和推理/评价代码；重放另按原分析 manifest 核对全部回执、开始记录和余额恢复登记的字节及完整清单。原分析 manifest 自身也固定指纹，不能通过删除或改写它绕开检查。

[replay_bindings.json](replay_bindings.json) 是本次事后新增的溯源绑定，以 run_003 的冻结 manifest SHA-256 为键，固定原分析 manifest 及虚构测试 `run_001/normalized.json`、`run_002/summary.json` 的路径、哈希和计费字段。金额仍来自已保存文件，不扫描后续测试目录；来源变更、缺失或未登记的 run 会报错。它不修改旧 manifest，也不是新的推理预注册。未来其他 run 须显式登记自身来源，不能继承本轮费用。

执行者自查材料见 [历史修订说明](../../outputs/004_event_alignment_pilot/verification_live/run_002/README.md)。随后独立复核亲自运行 81 项现有测试、41 项隔离篡改检查及两次完整离线重放：15 个结果文件均与原结果逐字节一致，仅诊断、来源元数据和重放指纹等发生预期变化，两项原问题已关闭。当前正式科研结果仍为 `run_003/analysis/report.md`，旧报告／verification 中的待审计状态属于历史快照；当前状态以独立审计末尾结论和本说明为准。
