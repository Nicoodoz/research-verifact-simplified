# 071：医生标注示例驱动的 Judge 上下文学习可行性验证

冻结时间：首次 071 收费 Judge 请求之前。本协议只允许一个固定的四示例方案；不搜索示例组合、prompt、模型或后处理。`outputs/service_tools/aliyun/key_check_20260923/attempt_006` 的工作空间可用性测试计入预检，历史尝试保守预留合计 ¥0.60 一并计入本任务预算安全余量。

## 研究问题与来源

固定 053 的 C48→final reference、`deepseek-v4-flash-0731` 的 T-S thinking-high scoring Judge、及 053 冻结的 PriorG 参数。原 VeriFact 固定源码 `f115d36.../packages/llm_judge/src/llm_judge/prompts.py` 对非推理 Judge 使用三个**合成** few-shot 例子（NS、S、NA）；推理 Judge 使用无例子的 reasoning prompt。当前 053 T-S 提示也无示例，另要求五项 checks 和三类 label_scores。本轮只在原 T-S 系统消息末尾追加四条真实医生标注示例；原系统指令、目标 user payload、JSON schema、Judge 参数和 PriorG 完全不变。

## 患者与示例（首次调用前锁定）

以 053 冻结 40 名 development 患者、每人 6 条 claim 为母体。按 `SHA256("071/eval/v1:"+sid)` 升序取前 16 人作评价，共 96 条**全部纳入**：GT S=78、NS=5、NA=13；其余 24 人作教学示例来源，评价病例不得因难例或历史模型输出剔除。患者、病例和完整 reference 指纹写入冻结台账。不用 reserved。

固定四条教学示例，均取 053 冻结材料且三名医生首轮标签完全一致、无二轮异常或时间元数据冲突：

1. `ede1dbb2...`（patient 65399，S）：extubated without incident；使用对应 final reference 中完整、直接记载已拔管的第 6 个 EHR block。
2. `0d286baf...`（patient 97212，NS）：leukocytosis due to pulmonary infarcts；使用**整个** 053 final reference，保留相关白细胞增多及不同病因描述。
3. `6446f0a7...`（patient 67117，S）：dehydration in setting of diarrhea and acute infection；使用完整的相关 physician EHR block，其中直接叙述该关系。
4. `b90878f5...`（patient 72844，NA）：posterior superficial compartment pressure 45 mm Hg；使用**整个** 053 final reference，保留其他 compartment syndrome 内容，同时核对没有该具体测压事实。医生 NA 来自原标注的完整 EHR 视野；这里不能声称任何短片段的“无记载”即等于完整 EHR 阴性。

只展示 claim、真实 EHR 证据和医生 label；不生成“标准 reason”。示例病人 ID 不进入提示。离线检查四例与评价患者互斥、无相同 claim/来源 note ID、无高相似近重复；如检查失败，停止并说明，不删除评价难例或事后换示例。示例真实标签仅用于教学，不用评价患者 GT 或历史干预结果构建请求。

## 三个固定输入

- **B，同期原包基线**：与 053 T-S 完全同请求体；重新调用以测量时间/同输入波动，053 历史回答只作辅助参照。
- **E，正确对应示例**：系统消息追加四条 `proposition/reference/physician_label`，固定顺序如上；目标 user payload 与 B 字节一致。
- **C，打乱标签对照**：与 E 使用完全相同的示例 claim、reference、顺序、结构、标签总数和近似输入长度，仅把四条 label 按固定映射换为 NS、S、NA、S；四条均与医生标签错配。它检验具体证据—标签对应关系是否提供超出格式、长度和类别比例的增量。C 只作机制对照，不是候选方法。

三臂均 `model=deepseek-v4-flash-0731`、`enable_thinking=true`、`reasoning_effort=high`、`temperature=0`、`max_tokens=8192`、`stream=false`，保持冻结 JSON schema。一个预检用非评价的短虚构输入，只确认模型可用、reasoning 和结构有效；若模型/模式不符或请求失败，停止，不切 Qwen、模型别名或其他端点。

## 发送、重复和停止

先对 96 条各发 B/E/C 一次（288 次），请求次序由 `SHA256("071/job/v1:"+id+arm)` 固定。全部成功回答只调用一次，不因结果重发。若预检失败、源码/输入指纹不符、患者隔离失败、任务实际费＋在途/未知预留将超 ¥20，立即停止并保存状态。

第一轮后的**事前 gate**：最终 PriorG 的 E−B 净正确至少 +5，E 的 false-S 增量≤1、MCC 不下降，并且 E−C 净正确至少 +3。未达任一项即停止，不追加版本或重复。达到后，在同一 96 条上独立重复 B/E 的完全相同请求体各一次（192 次），用于确认系统净收益与同输入波动；C 不重复。若预算不足，保留重复性不确定，不缩减关键对照以宣称成功。重复确认要求两轮 E−B 均净正确≥+5、false-S 增量≤1、MCC 不下降，且第一轮 E−C≥+3；还应报告逐例 rescue 在第二轮是否保留。bootstrap 区间另报，不把点估计当显著性。

T-S 核心无效不重跑 HTTP200。raw verdict 若可解析则单列；raw 同 ID 主比较只在三臂都有效的完整共同集合上评价，缺失 ID 与覆盖另报。系统 PriorG 若某臂无合法 scores，按 053 冻结的该 ID 同期历史 N-S U2 预测作事前 fallback，维持 96 条完整同 ID 主分母并标出每个 fallback。报告原生 raw、PriorG 后 PA/AC1/MCC、false-S、S/NS/NA recall、配对 rescue/harm/net、患者 cluster bootstrap 1000 次和患者方向。推理文本、引用只能作诊断线索，不作内部机制证据或新增医学 GT。

## 费用与交付

用户本轮把新任务累计收费 API 上限更新至 **¥20**。历史 053 T-S 均价约 ¥0.02657/次；四示例令 E/C 输入更长，估计第一轮约 ¥11–13，若 gate 通过全量 B/E 重复再约 ¥6–7；含已存在的保守预留 ¥0.60，总估计不超过 ¥20。每次按实时公开价格与 `max_tokens` 做在途预留、收到 usage 后入账；所有预检、失败、重试和未知预留不因换 key/阶段重置。超过上限或无法合理估算则先确认；不为追求阳性改标准。

保存协议、四条示例完整来源及裁剪理由、患者清单/近重复检查、精确请求、逐次回执/费用、评价、完整性自检和中文报告。阴性结果照实结项；不自动 072、不自动 commit/push。
