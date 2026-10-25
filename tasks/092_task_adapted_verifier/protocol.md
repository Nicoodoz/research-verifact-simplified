# 092 任务适配的临床证据核验模型：事前协议

起始main及origin/main：59931200633ad105d6a4be1da81f23c87962b744。
用户092新授权允许全部既有患者标签参与训练和模型选择，包括历史reserved角色；不更改036原评价历史。本轮是暴露数据的患者分组OOF，不称全新holdout。

## 科学变量与历史区别

032的nli032.py使用inference_mode冻结DeBERTa，CLS规范化后投影32维；learning032.py学习聚合头，并读旧LLM分数和残差。037只读分数；042/044/046/049为选证、结构或判定干预；066/068/069是oracle/证据效用诊断；083是固定理由特征分类。未发现等价的医生监督encoder微调。092只改变文本encoder顶部层是否更新，不输入旧LLM分数、理由或PriorG。

## 数据与固定证据

9065条有效claim、100患者。7248条直接复用032/036逐字C48；1817条使用原008/009切段、两路交替48候选及原packing，032以外已下载021 BGE本地权重补齐。021未证明API逐字等价，故来源分别报告，不将新增本地包冒充既有API包。claim不截断，reference完整以重叠token窗口覆盖；所有窗口进入模型，不按GT或模型分数选窗口。

## 唯一主结构与有限训练

MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli，032锁定revision b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7；24层、1024维。窗口512 token，证据在前、完整claim在后，证据相邻窗重叠32 token。每窗1024维CLS，单头标量attention加权均值，LayerNorm、dropout0.1、线性三分类。没有NLI三分数或随机投影输入。

Frozen：全部encoder固定；Fine-tuned：仅第24个transformer block更新。共享relative embeddings及前23层固定为eval，可缓存其完整token隐藏表示；不是只训练一个外置MLP。冻结与微调顶部层均关闭encoder dropout，以保持缓存/在线等价和单一训练变量；分类头dropout相同。先用实际前向及反向验证缓存拆分与原模型的一致性、梯度和参数变化。

仅普通CE为主，不追加backbone、loss或aggregation搜索。AdamW，顶部层lr=2e-5、分类头lr=1e-3，weight_decay=0.01，梯度裁剪1，最多5 epoch，effective batch=8 claims，窗口小批执行。两模型相同种子、输入、头和训练/验证患者。epoch在每个outer fold的内部患者validation按(MCC, PA, Macro-F1, -false-S)字典序选择；不看outer标签选epoch，不根据全量OOF成绩换方法。缺失类别指标固定三类。

外层5折，患者ID固定hash排序轮转；每折20患者预测，其余80患者按另一固定hash抽16患者作内部validation、64患者实际梯度训练。最终每条OOF的全部权重选择与训练均排除其患者。为节省一次额外训练，直接使用内层选出的64患者训练模型预测外层，不在80人重训；每位患者跨折参与训练。所有fold都有两个模型结果，不能因首折差而停止。

## 资源与恢复

本机RTX3060 Laptop 6GB。冻结底层缓存为计算优化，完整1024维、float16、不随机投影。若缓存超过D盘安全余量，私有激活可放E盘任务专属目录并记录绝对路径；不纳入Git。模型、原文与checkpoint在.local_models/092；不改.gitignore。恢复只跳过哈希匹配且完整阶段；训练保存优化器、随机状态和进度。工程失败不解释为科学阴性。新增API≤¥30，本计划0 API；本地运行时单独报告，不虚构电费或租金。

## 评价与可选融合

全OOF与原作者同ID；B/F4缓存采用固定来源优先级078→082→084→090，每ID首次来源，不看对错选回执。同ID比较同时核对C48绑定。报告全部三类指标、PA/MCC/AC1/Macro-F1、false-S/non-S及predicted-S假发现率、作者、患者、历史角色与C48来源分层、NLL/Brier/ECE、配对救回/伤害与患者bootstrap。

融合不是默认阶段：只有独立模型接近强基线、少数类/false-S明显改善或存在有意义互补时才启动一个固定线性logit融合；必须患者隔离训练且文本表示模型不能通过别的fold间接看外层患者。若无法满足此交叉拟合条件，明确不以泄漏的全量OOF训练融合冒充患者外增益。不得为救成绩连续搜索。

## 交付

完整报告、架构/训练/OOF与基线表、类别与病例、成本/哈希/复现和自检。结果足够强时另存091论文的新版本，不覆盖旧稿。执行者自检非独立审计。完成commit/push并停止，不自动093。
