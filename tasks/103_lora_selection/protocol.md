# 103：微调模型选型与小规模可训练性验证

2026-10-27用户专项授权，第一阶段止于READY_FOR_GPU。102封板不动；不买实例；收到用户连接后才运行GPU。API硬上限30元，目录价；GPU及相关存储另计60元且最多8小时，含加载/编译/预跑/评价。两账跨恢复累计。

## 数据及固定面板

沿既有development40为训练、exploration20为选型、reserved_test40为后续确认。本轮仅登记后续40身份，不新增评价或模型选择。全部100人历史暴露，不称未见holdout。母体为092核对的9065条有效atomic、医生最终标签，连接原作者v1.1.0-rater-121发布reference，逐条验证SHA及身份；不输入C48或生成理由。

在新成绩前冻结共同主面板240：自然160，额外NS/NA各40。先冻结其中本地/缩量180：自然120＋NS/NA各30，再按相同规则补40＋10＋10，保证嵌套。自然按GT×作者比例最大余数分配并用103固定SHA排序；压力按作者比例。48直接模式为三类各16、24重复为三类各8，均在180子集中按固定hash选。训练512为S320/NS96/NA96，患者轮转分散；前256为S160/NS48/NA48。哈希不依赖历史对错、模型结果或长度。完整reference禁止截断。

## API设置、预算及工程规则

四模型固定qwen3.5-27b、qwen3.8-27b、qwen3.5-35b-a3b、qwen3.6-35b-a3b。同原作者式简洁任务，temperature0、top_p1、repetition_penalty1、n1、streamfalse；native开启thinking_budget4096，最终max_tokens768，输出verdict/reason。3.8官方映射4096为low，不同时传reasoning_effort；相同上限不保证内部推理等效。label关闭thinking，仅输出verdict JSON、max_tokens128，删除reason要求，其余定义原样。

先固定自然/压力各2条四模型native及固定2条四模型label（共24个可复用正式请求），只检查usage/模型身份/格式/截断，不连接正确率。整体预算使用真实token长度及099输出usage，首批完成后用本轮usage更新；预留输出均值20%及必要通信余量。优先240＋重复24/模型，若不足取消重复，再统一180；不得按首批成绩缩量。可选重复决定在分类分析前锁定。没有缓存优惠假设，实际账本同时报目录实耗和无缓存保守额。

单请求发送前以UTF8字节上界、思考4096＋最终上限＋32、对应价格档位原子预留；并发受同SQLite总账约束。未知计费保留预留，未成功最多3次有限通信重试；HTTP200不按结果重发。明显截断先停剩余派发，工程修正另记、原答保留，不将截断判作医学能力失败。完整外JSON围栏可规范化，禁止从解释中搜索标签；其他格式记invalid，不补NA。

## 选型及评价

自然/压力分报；原作者paper_r1单列历史参照。共同有效及各自覆盖、全N已知正确下界并报，统一evaluate/paired_compare、1000次患者bootstrap、三类PRF/MCC/PA/Macro-F1/false-S及分母、患者/作者层和逐例转移。重复不替代首次。

API大模型选择先看自然MCC，MCC差≤0.02为实用近邻；兼顾PA（不得比最高者低超过2个百分点而无风险收益）、自然false-S、压力NS/NA及label48。同面板label相对native排名反转且净正确差至少3或MCC差≥0.05，纳入推荐而非忽略；不按API单价淘汰3.8。近邻优先false-S少、NS/NA较均衡、BF16可运行者。近邻不够明确则保留待测者，不宣称唯一最优。9B固定低成本GPU候选；只读查API存在且明确单价才用API，不用Flash替代。

## GPU预备与第二阶段

独立Python3.12、CUDA/PyTorch支持Blackwell、Transformers v5和PEFT/经核实方案，固定依赖与权重revision、模板和tokenizer SHA。BF16 LoRA r16/alpha32/lr1e-4、micro1/accum8、gradient checkpointing、1epoch；冻结视觉、基础权重，只监督真实verdict，prompt/padding为-100。MoE逐个专家参数核查覆盖，不能把激活3B当总显存。

真实长度3—5优化步骤覆盖中位/长尾，记录首次编译、前反向/optimizer/峰值显存/token/s及native生成速度；预跑权重丢弃，正式从同初始revision开始。用实测预算先留两模型各180×3臂必要评价，再决定各512或各256，不能看效果再缩量。256只存checkpoint/过程，512结束；native_base（thinking verdict/reason）、label_base和lora_label（同直接模式）必备。API/本地固定小桥接核查模板/接口差异，不从API减本地成绩计算微调增量。仅当两候选完整对照有预算时考虑第三近邻。

GPU保存/恢复/关机仅作用于本任务实例，先备份结果，不删除数据。第一阶段报告估算而非伪报GPU实测；正式训练成本按40人全训练token及后续确认token外推，最终推荐看训练后绝对质量、不奖励低起点。第一阶段完成推送两个仓库并暂停等待连接。
