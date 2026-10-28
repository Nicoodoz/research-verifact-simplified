# Research-VeriFact

107训练、1000条评价、关机后CPU分析完成。107结论：当前support_aux配方没有提供可辩护的整体核验收益，建议停止扩大。 NS识别明显改善，但以NA识别明显下降为代价；自然面板MCC与PA下降，压力面板MCC基本持平、false-S增加1条。自然false-S减少2条不足以抵消总体损失，不在这500条上调权重、采样、阈值或轮数挽救结果。 两臂各196×2轮/50步，推理无辅助头；原GT/reference/105主loss保留。用户确认关机，GPU估算¥4.560、API0，精确账单待核。原始回执与最终完整optimizer/适配器已回传核验，不自动启动108/扩大或升级默认。 [107当前报告](outputs/107_support_aux/final_report.md) · [实时进度](outputs/107_support_aux/实时进度.md)。

临床文本与患者EHR的一致性核验研究。102已完成零费用可行性核查并在付费分类前停止；不是分类效果阴性。[102报告](outputs/102_demo_relation/report.md) · [101正式分类报告](outputs/101_nsna_review/report.md)。默认不变。

## 总体目标

总体目标是在 VeriFact 数据集上，以公平、可复核的实验比较超越原系统。公平对比至少保持相同推理模型与设置、相同评价ID和标签口径，并交代证据、监督及成本差异；原作者发布的不同模型预测只能作历史参照，不能替代同模型强对照。不要求所有指标全面领先，允许少部分指标有合理代价，但必须同时报告PA、MCC、false-S及三类表现。

MCC 和 false-S 相对更重要：前者反映类别失衡下的整体分类质量，后者反映错误放行风险，二者更能支撑论文的方法价值与风险取舍论证。这里“宁愿多判，也不能漏判”指临床文本核验中宁可适度多报疑点，也尽量避免漏掉真实不一致；false-S 是GT为NS/NA却被判为Supported。它不是疾病诊断的漏诊率，也不意味着把所有命题都判为有问题。不能用严重类别塌缩或大幅准确率损失换取好看的单项指标，更不能为了论文故事改变评价口径。

当前研究优先证明前处理和Judge原生判断（raw）的收益，不以更强模型替换或Frozen PriorG后处理的收益代替这一目标。历史默认系统仍为C48→DeepSeek V4 T-S thinking-high→Frozen PriorG、无示例B；这是已冻结配置，不是对未来方法的强制要求，也不表示已实现同模型raw超越。新实验和默认升级仍需明确授权。

## 当前证据

101 NS/NA定向复核已结项：确认600自然＋100压力、282触发双臂、24条双臂重复。自然共同597条，verifact_ref/nsna_plain/nsna_review正确496/494/496，MCC 0.6376/0.6237/0.6331；false-S均11，Supported集合逐条不变。plain：失败停止；review：失败停止；对应检查实际增量门槛=False。新增费用及预留¥25.227232/30，默认不变。[101完整结果](outputs/101_nsna_review/report.md)。下面097表保留历史强对照背景，共同158条：

| 配置（raw） | MCC | PA | 正确数 | false-S |
|---|---:|---:|---:|---:|
| 发布reference＋V4简洁任务 | 0.5367 | 79.11% | 125/158 | 3 |
| C48＋V4简洁任务 | 0.5625 | 79.11% | 125/158 | 2 |

点估计体现MCC和错误放行的有利取舍，**尚不能声称稳定超越**。这是原作者式接口适配，并未完整复现作者的辅助格式整理链；两种reference内容和长度也不同。主Judge和评价ID相同不等于所有操作完全相同。[097完整报告](outputs/097_native_judge_source_dependence/report.md)保留有效性、波动、区间与阶段B未启动的原因。

095的8997条主表比较过原作者发布预测与V4＋PriorG，但同时改变模型和后处理，不能用来证明当前目标下的同模型raw方法胜出。100名患者均已有历史研究暴露，不再称有全新未接触holdout。详细结果和旧实验适用范围见[项目现状](docs/PROJECT_STATUS.md)与[任务索引](docs/TASK_INDEX.md)。

## 常用文件

| 要看什么 | 位置 |
|---|---|
| 当前状态、已完成结果与限制 | [PROJECT_STATUS](docs/PROJECT_STATUS.md) |
| 执行规则、预算与环境 | [AGENTS](AGENTS.md) · [API政策](docs/API_POLICY.md) · [运行环境](docs/RUN_ENVIRONMENT.md) |
| 导师汇报中的前处理与推理结果 | [汇报文档](docs/reports/2026-10-15_导师汇报_前处理与大模型推理.md) |
| 历史论文底稿（截至095） | [完整稿](outputs/095_anchored_minimal_contrast/manuscript_zh.md) · [后续修改指南](docs/papers/02_revision_handoff_zh.md) |
| 复查与独立审计 | [复现说明](docs/REPRODUCIBILITY.md) · [审计索引](reviews/README.md) |

`src`是共享实现，`scripts`是操作入口，`tasks`保存每项实验的协议和代码，`outputs`保存结果，`tests`是代码测试，`reviews`是实际独立审计，`docs`是规则与研究资料。旧报告、旧提示词、来源快照和审计按形成时解读，不作为当前指令。

## 运行与发布

CPU/API主环境为`research-verifact-029`，统一用`scripts/run_research.ps1`启动。2026-10-26用户授权将新千问AI端点及已验证Key设为默认，加载根目录.env.aliyun；默认模型deepseek-v4-flash-0731、thinking-high。极简及thinking-high合成请求均已HTTP200成功，但不代表冻结临床prompt或旧平台科学等价已验证。历史GPU环境和正式任务的冻结请求仍分别遵循原协议。

本地保留完整研究材料。只有你明确要求推送时才提交/发布；只说“推送到GitHub”默认同时更新两个仓库：[完整归档仓库](https://github.com/Nicoodoz/research-verifact)保留全部允许发布的outputs成果，[精简阅读仓库](https://github.com/Nicoodoz/research-verifact-simplified)的outputs只保留关键成果。两仓库outputs之外使用同一份当前允许发布文件快照。明确要求只推其中一个时按该次要求执行；数据、密钥、私有回执和模型缓存不因完整归档而公开。具体约定见AGENTS。
