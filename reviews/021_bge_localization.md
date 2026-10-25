# 021 快速独立审计

**2026-09-19：PASS，可冻结／结项。严格冻结等价性仍为FAIL；本地可运行不等于可以继承020成绩。**

被审HEAD：4681fee466910f36cd10c13c3ba51092b2181ec3，加未提交021源码、输出及现行导航。原[主报告](../outputs/021_bge_localization/report.md)、manifest和交审文件保留原字节；52项冻结文件指纹全部匹配。

- 对保存FP32向量重新构建879条dense/C48及rerank pair，6个比较内容文件字节一致；候选、pair、逐条比较和汇总均可重建。
- 固定API C48只换reranker：594/879 reference完全一致；全本地：565/879一致。协议要求879/879有序selected_ids及reference同时一致，因此FAIL正确；未用高cosine/Spearman代替门槛。
- 本地权重逐字节SHA-256匹配登记值。embedding另核对[固定HF revision权重页面](https://huggingface.co/BAAI/bge-m3/blob/5617a9f61b028005a4858fdac845db406aefb181/pytorch_model.bin)；reranker上游页面本次浏览不可达，其本机哈希与既存固定revision登记一致，不声称本次重新下载验证。
- 用本地tokenizer关闭截断，重新计算全部49246个pair长度：最大319，512上限不截断。未重跑GPU推理；保存的数值输出与本机环境版本、权重绑定已核对。
- FP16/FP32选择依据是API向量／候选相似度，未发现实现代码通过GT/Judge成绩选择条件。参数诊断和失败版本保留；不将工程对照称新性能实验。
- 021新付费API为0，复用020已用10名development患者，未用reserved test。共同265项回归通过；新增安全重放入口4项保护测试通过。

## 交付问题及已完成处理

原021 README的“重放顺序”会运行GPU并覆盖固定成果；verify021.py会重写历史verification_001且含“gitignore未变”运行期条件。它们作为冻结历史源码保留，日常入口改为[安全离线重放](../docs/REPRODUCIBILITY.md)，写入新目录并禁止网络；不改旧manifest来掩盖变化。生成器简版report与人工整理正式report为不同版本，复查比较6个机器文件，正式报告保持。

模型原先仅通过本机exclude排除；用户本轮明确授权后，新增共享/.local_models/及/outputs/replays/忽略规则，未泛化忽略.npy/.jsonl。新增environment.local-bge.yml，保持root环境计算依赖不变；已核对关键包版本，未宣称新建空环境安装已实测。Git属性保证019–021冻结代码在Windows检出后保留原字节。

本次PASS是成果可复查性与解释边界通过，不是临床部署认证或跨硬件确定性保证。020成绩仍属于API-BGE，任何后续本地实现的科学评价需另行冻结；不自动开展reserved test。当前[任务入口](../tasks/021_bge_localization/CURRENT_STATUS.md)与[联合审计附件](artifacts/019_021_audit_20260919/README.md)为后续依据。
