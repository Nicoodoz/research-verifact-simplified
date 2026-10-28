# 104：训练监督诊断与证据短理由数据构建

本轮仅准备数据和CPU接口，不训练、不启用云GPU、不恢复27B、不下载模型权重。当前数据规模以最终manifest为准；构造成功不代表分类提升。

## 数据及输出格式

- 原始512训练正文：`.local_models/104_supervision_evidence/train512_original.jsonl`。与103原训练集完全同ID、患者、GT及reference；不能把选型180或后续确认患者材料加入。
- 首审288正文与台账：私有`blind_cases.jsonl`及`review_root.jsonl`、`review_b.jsonl`、`review_c.jsonl`。原GT钥匙独立存储；完整首审副本和SHA封存后才允许构建工具join GT。
- 初步候选：私有`candidate_paired/label_only.jsonl`与`candidate_paired/evidence_brief.jsonl`，不是最终质量通过声明。
- 首次连接GT的稳定副本是私有`review_joined_initial.jsonl`，原candidate manifest及教师队列绑定它；`review_joined.jsonl`只是当前态，后续最终修订不会覆盖initial副本或使原candidate来源SHA失效。
- 教师逐条核查后的候选：私有`candidate_teacher_checked/`两份文件；保留原blindcandidate不变。该阶段明确记录真实沿用、修订、拒绝教师而保留盲稿、新草稿或隔离，不能将“核查过”计为理由复用。
- 明确接纳后的最终包：私有`paired/label_only.jsonl`与`paired/evidence_brief.jsonl`；公开`paired_manifest.json`只含规模、标签/来源分布、ID和SHA，不含临床正文或短理由。未审查224条S不会自动进入包。
- 标签对照答案：`{"verdict":"原医生标签"}`；理由答案：`{"evidence":["少量原文引句"],"relation":"简短事实对应说明","verdict":"同一原医生标签"}`。

每行`answer`是**JSON字符串**，`answer_text`是完全相同的字符串；两者不一致会拒绝加载。GT作为元数据保留，不写进输入payload。两臂同ID、患者、GT、claim、reference、messages和顺序，仅监督答案不同。NA没有相关anchor时可经完整语义审查采用空evidence，不根据关键词未命中自动生成。

`metadata.evidence_spans`逐引句保存quote SHA和全部精确`occurrences`，每处含start/end和可解析来源。重复引句不能随便挑首处；源码未发布原note ID时保留null，显示编号不是note ID。实际引用/关系原稿和修订记录均留私有，公开台账只给状态和指纹。

## 既有教师理由的真实复用

全部288首审封存并生成原blindcandidate后，才可运行：

```powershell
python -B tasks/104_supervision_evidence/teacher_queue104.py --export-queue
python -B tasks/104_supervision_evidence/teacher_queue104.py --apply-decisions .local_models/104_supervision_evidence/teacher_decisions.jsonl
```

第一步逐候选重新核对claim与reference SHA、reference ID及原GT，教师预测须等于原GT且reason存在；固定优先R1-70B，其余按model ID/rater_alias排序，不读取103对错。输出私有`teacher_queue.jsonl`与公开去正文manifest。此时没有语义接纳，不能只凭标签一致当作可靠理由。

人工/子代理decision每条含`id`、`action`、`reviewer`、`semantic_checked=true`和具体`grounding_assessment`。存在教师时须给原reason SHA。`reuse`保持原reason原字不动；`revise`须给最终relation、真正保留的`retained_teacher_facts`及`revision_notes`；拒绝教师而保留已有盲稿记`reject_teacher_keep_blind`；没有合格同源教师才记`new_draft`；不能可靠解释则`quarantine`。原文引句仍逐字定位，程序不以词重合认证关系。

第二步生成独立`candidate_teacher_checked`配对包及去正文`teacher_provenance.jsonl`，完整教师原文、首稿、修订说明和decision SHA快照均私有。之后固定质量/API核查应冻结这份包；最终paired需承接这份答案及来源，不能重新退回未经教师核查的blindcandidate。

最终`build104 --build --decisions`的每条决策可带`supervision_metadata`，只允许`teacher_review`、`relation_origin`、`teacher_semantic_reviewed`三个来源字段。它们对称写入两臂metadata，不改变claim/reference/GT，也不能覆盖prompt或引用偏移。传入的relation与evidence仍须是教师核查后的最终版本，原首审和显式修订历史均保留。

## 与103训练代码的接入差异

`training104.messages(claim,reference)`是两臂唯一prompt入口，两臂都允许可选evidence/relation及必需verdict；Input JSON只包含text/reference。它不是偷偷给理由臂另加提示，也不将医生标签或审查状态注入prompt。

`training104.encode_lists(tokenizer,row)`保持103的返回签名：`(input_ids, labels, supervised_token_count)`。prompt全部为-100，**完整answer及结束标记参与loss**；`pad_batch`将padding loss也设为-100。`encoded(tokenizer,row,torch,device='cpu')`提供103形状的张量接口，默认CPU，不加载权重。

未来训练必须调用这个答案编码入口。103的旧`encode_lists`会硬编码`{"verdict":r['GT']}`，直接照搬会把理由监督丢掉，即使读取了evidence_brief文件也仍在训练标签版。

103的`training()`还固定读取`train512.jsonl`、每8条执行一步、loss除8、`samples += 8`，并用精确样本数判断最终保存。筛选后的N可能不是8的倍数，照搬会低估尾批loss、把实际消费数记大，甚至漏掉最终checkpoint。本轮保留103原代码不改；提供CPU计划函数作为未来最小接入点：

|原103假设|未来接入要求|
|---|---|
|固定读取train512|明确加载本轮选定臂文件，读取最终manifest中的实际N|
|答案由GT重建|调用training104.encode_lists，监督行中完整answer|
|loss固定除8|按optimizer_batches给出的loss_divisor，即当前实际微批数归一化|
|samples固定加8|记录当前batch.end_sample，保留真实消费数|
|只在固定倍数或samples==N保存|使用checkpoint_due，实际尾批必须保存|
|默认512/64步|按真实批次记录optimizer step，总数为ceil(N/8)，不丢尾、不补样本、不重复样本|

`optimizer_batches(rows,gradient_accumulation=8,start_sample=0)`只返回CPU批次计划，不执行训练。每条仍对应一个microbatch；每条模型mean loss除以该批`loss_divisor`，保持等样本权重。比如N=19，批次为8/8/3，最后3条分别除3，消费终点8/16/19，总3步。它不是把不同答案长度转换成新的类别权重。

恢复仅接受已完成optimizer batch的真实消费offset；完成后的N offset返回空计划。不能从累积一半的样本号静默恢复。两臂必须使用相同原始次序、微批计划和恢复规则。新训练器还须另行实现权重/optimizer/RNG检查点和资源预算；本轮没有实现或运行GPU训练器。

## CPU验证与运行

```powershell
python -B tasks/104_supervision_evidence/test_training104.py
python -B tasks/104_supervision_evidence/test_build104.py
python -B tasks/104_supervision_evidence/test_public_scan104.py
python -B tasks/104_supervision_evidence/test_teacher_queue104.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/104_supervision_evidence/check_interface_cpu104.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/104_supervision_evidence/tokenize104.py --pair-dir .local_models/104_supervision_evidence/paired
```

tokenizer检查复用已有tokenizer-only环境和103固定9B revision，不安装升级，不加载基础权重。候选长度检查需显式传`--pair-dir .../candidate_paired`；最终长度、配对规模和类别覆盖以实际包产生后的统计为准，不能用纯合成工程测试代替临床数据核查。

构建顺序、盲审封存及显式质量决策的命令见[BUILD_RUNBOOK](BUILD_RUNBOOK.md)。公开发布前运行`public_scan104.py`；这是模式与字段检查，不冒充临床隐私认证。正文与机器辅助解释不是新增医生gold，也不代表完整思考过程。
