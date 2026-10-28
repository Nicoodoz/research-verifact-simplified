# 105本地准备：READY_FOR_NOGPU

**本阶段已完成可直接接续的代码、真实数据与冻结配置；未访问AutoDL、未调用收费API、未下载权重、未训练9B、未产生105预测。新增计算租金/API/磁盘均为0。未commit或push。**

两个训练臂复用104原始字节的196条（S83/NS62/NA51，40患者），只改变监督答案。`base_judge`为未微调同9B新模板基线；`label_only`只训练分类JSON；`evidence_brief`训练冻结的短证据、关系和同一标签。两LoRA从原revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`初始化，不接103适配器。完整权重分片在本机不存在；已绑定103原分片SHA清单与本机固定tokenizer/配置，下一无卡阶段核对既有实例上的实际文件。

|已固定内容|实际准备结果|
|---|---|
|训练|BF16，r16/alpha32，lr1e-4，microbatch1，累积8，梯度检查点；其余AdamW/模块/种子沿103可用设置|
|轮次与顺序|原196顺序重复2轮，每轮24×8＋4，25步；每臂共50步、392次提交的样本消费，不挑epoch|
|分段loss|最终verdict值平均CE＋其余答案平均CE，JSON结构/EOS归其余段；prompt/padding不计loss|
|位置定位|串行构造时记录字段值字符区间，再由真实token offsets映射；392份答案纯边界检查通过，理由中同名标签不算分类段|
|效率与恢复|一次backbone前向，只投影答案hidden，16-token head/CE块重算；交替完整检查点保存adapter/optimizer/scheduler/RNG与真实消费数|
|自然面板|selection20中固定400，S321/NS26/NA53，human226/llm174|
|压力面板|另NS50＋NA50，与自然ID不重叠；human89/llm11|
|评价|三臂同104模板、thinking关闭、greedy、n=1、384输出，同一解析器与固定8行分组；不截断病历、不复用103预测|
|长度|最终训练最长12,821 tokens，完整共同上下文13,097；原文未裁剪|

评价患者与训练40人隔离，不读取确认40人的临床材料。500中70条曾在103选型180内；全部患者有历史研究暴露，不能称全新holdout。抽样没有使用103对错、长度或104解释是否合格。三臂自然和压力分开报告，保留完整N、有效覆盖、三类表现、MCC/PA/false-S和患者bootstrap；paper_r1仅历史参照。

晋级规则已在[协议](../../tasks/105_brief_supervision/protocol.md)冻结：相对label_only，自然ΔMCC≥0.02或false-S/non-S下降≥5个百分点，同时PA下降≤2个百分点、false-S增加≤2个百分点、NS召回下降≤5个百分点；压力false-S不增加、NS召回下降≤5个百分点。相对base_judge的MCC与false-S同时变差则不扩大。只作开发继续标准，不是论文确认；不得按结果改epoch、样本或后处理。

104统计错误已从原医生前三票重算核对：保留196中三人一致**92**条，unresolved 78中**21**条。修复了字符串/整数比较，保留旧冻结summary/报告及全部训练/回执，另存[更正说明](../104_supervision_evidence/agreement_correction_105.md)和[更正统计](../104_supervision_evidence/supervision_summary_corrected.json)。

本地6项CPU小张量/小模型检查通过：loss与梯度对照、因果位移和mask、单次backbone与有界head、两轮尾批/恢复/RNG/调度器/最终保存、统一解析器、继续判据与跨阶段费用账本。另完成真实196配对及500提示token核验、理由同名标签的对抗位置检查。另用纯模拟批次走通了保存格式→解析→统一评价→继续判据接口，三臂完全相同的模拟答案正确未通过改善门槛。测试没有加载9B，不能代替实际GPU路径验证。

按103实测5448 training tokens/s与直接推理吞吐、104短理由目标平均112.88输出tokens估计，GPU约**2.41小时**。用历史同卡6.98元/小时约**¥16.79**，另无卡预留1元约**¥17.79**，运行线18元、硬上限20元；API预算0，不新增磁盘。不把384上限当平均耗时；短输出批次拟合无法识别稳定decode斜率，所以预算使用更保守的长理由外推。实际报价、不同GPU速度及完整生成耗时下一阶段再验证，预算不足时保留固定任务并报告未完成，不缩水对照。

私有最小同步包约**5.67 MB**，43文件，已逐文件及归档内容核验：`.local_models/105_brief_supervision/sync105.tar.gz`。包含临床正文，不能Git发布；不含模型权重、凭据、103适配器或wheelhouse。SHA见[sync_manifest](sync_manifest.json)，方法/数据冻结见[preparation_freeze](preparation_freeze.json)。

**第二阶段读取[无卡交接入口](../../tasks/105_brief_supervision/NOGPU_HANDOFF.md)。** 先复用103既有磁盘、原始分片和venv，核对实际版本/SHA及392份答案和500提示在GPU环境tokenizer0.23.3下仍一致。当前本地tokenizer为0.22.2，已安排无卡跨版本核验，未假定等价。

仍需GPU验证：真实Unsloth/PEFT backbone与梯度、BF16分段loss/内核兼容和最长输入显存、384输出的KV/平均吞吐、完整两臂训练及三臂预测。已准备独立后台预算守卫与可恢复supervisor，实际计费从平台开机起算，无卡/GPU/重启共用同一账本，不能重置。

工件：[训练清单](train_manifest.jsonl) · [评价清单](eval_manifest.jsonl) · [训练计划](training_plan.json) · [token统计](token_summary.json) · [费用估计](cost_estimate.json) · [零费用账本](cost_ledger.json) · [本地自检](readiness.json) · [代码入口](../../tasks/105_brief_supervision/README.md)。
