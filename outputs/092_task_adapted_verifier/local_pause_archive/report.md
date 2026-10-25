# 092 当前情况与暂停交接

**状态：PAUSED_BY_USER，研究未完成。** 2026-09-27约17:06（香港时间），按用户“整个任务停了，包括训练进程，写好当前情况文档，然后推送到github”的指示终止训练和父级流水线。后台监控已停止，不自动恢复。此报告是暂停交接，不是最终科学报告，也不把中断当成方法阴性。

## 已完成的材料与实现

- 核对开始时main与origin/main均为59931200633ad105d6a4be1da81f23c87962b744；暂停收尾时再次fetch确认无上游变化。
- 已阅读历史实验并确认032没有做等价encoder微调。092使用完整1024维表示和独立分类头，不读取旧LLM score；Frozen只训练聚合/分类头，Fine-tuned额外更新DeBERTa第24层。前23层固定缓存，不能称为24层全量微调。
- 9065条有效atomic claim、100名患者全部纳入；S/NS/NA为7035/693/1337。30条原invalid atomic不混入，原医生GT不改。
- 用户本轮明确授权使用全部已有患者和标签，故采用五折患者分组OOF；每折64人梯度训练、16人内部验证、20人外层预测。包括历史reserved角色的材料，但不改写036历史、不称为新独立holdout。
- 7248条C48复用历史冻结reference；1817条缺失输入用既有C48规则和本地BGE补齐。新增本地FP16分支不声称与历史API逐字等价，两臂使用同一冻结输入。
- 47219个512-token窗口已经全部编码并缓存，保留完整命题和全部C48 token覆盖。绑定输入SHA及代码、配置指纹已保存。
- 同ID原作者结果与956条B/F4缓存对照已准备；历史混合选样不代表全量自然组成。评价、可选融合、部署推理及复现脚本已编写，未执行部分不冒充验证完成。

方法详见[架构](architecture.md)、[冻结协议](../../tasks/092_task_adapted_verifier/protocol.md)、[历史核对](history_review.md)。

## 停止时真实训练进度

|部分|当前状态|
|---|---|
|Frozen fold0|完成5轮，内部验证选第3轮；已输出1902条外层预测及complete标记|
|Fine-tuned fold0|完成前4轮；第5轮在5685条训练序列的第1024条检查点暂停|
|Frozen/Fine-tuned fold1—4|尚未启动|
|完整9065条双臂OOF、统一主分析|未完成、未运行|
|融合、完整部署时延、代表病例、最终论文更新|未运行或未形成|

检查点读取验证成功，保存模型、优化器、混合精度scaler、随机状态、epoch和训练游标。Fine-tuned fold0内部验证暂选第3轮，**不是外层成绩或最终研究结论**。没有根据局部成绩改架构、loss、学习率或患者划分。

精确状态见[pause_snapshot.json](pause_snapshot.json)。冻结模型的1902条预测仅为部分工件，不据此评价全量竞争力。不能回答“微调优于Frozen/原VeriFact/B/F4”或“方法失败”；也未触发融合决策。

## 私有工件与恢复

原文和权重不推送GitHub，位于已有ignored目录：

- .local_models/092/inputs.jsonl：完整claim/reference，SHA 2b5e6bd2b91d385a9ca273f6affa18632aeb0228a34b40ef98fcbf645f84b0aa。
- .local_models/092/finetuned_fold0/resume.pt：恢复检查点，153382001字节，SHA 1c626f50ab588d4c84ea75b0a0a50502a0b77a098a7e566dbdce592efdb003ad。
- .local_models/092/finetuned_fold0/best.pt：当前内部验证最佳权重，尚非完成模型；其SHA见暂停快照。
- .local_models/092/frozen_fold0：完成的Frozen权重及检查点。
- .local_models/092/activations：指向E:/Research-VeriFact-private/092/activations的目录junction，约49.5GB激活缓存；不清理、不移动。

**只有用户另行明确恢复后**，先确认私有工件和E盘路径仍存在、哈希与有效冻结v3一致，然后归档任务目录的PAUSED_BY_USER.md。恢复入口如下；该命令此次没有执行：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -u tasks/092_task_adapted_verifier/continue092.py
```

入口会复用完整cache及Frozen fold0，从Fine-tuned fold0的epoch5/cursor1024继续。强制停机后检查点之后的少量未保存计算可能需重做；这不涉及收费API或挑选模型回答。不要重跑材料构造、删除旧结果或并行启动多个runner。入口新增暂停标记检查；不得绕过标记直接调用训练脚本。

后续仍需完成其余模型、统一全量评价，依据实际独立信号决定是否运行预登记的唯一融合，完成成本/风险/病例分析和最终报告、自检；符合条件才更新论文。benchmark092.py及其他未运行分析脚本仍需在实际执行时验证。

## 工程记录、费用和限制

有效训练冻结为training_freeze_v3.json。v1/v2原样保留：窗口microbatch从2到8只改变训练批处理，不改变已编码输入；首个正式batch前修正Windows标签张量int32为int64，未根据评价结果改方法。分别见cache_config_compatibility.json与training_numeric_fix.json。

已完成本地C48约1075秒、编码约3029秒、Frozen fold0约75秒；微调恢复检查点记录约1939秒，最后进度记录约1947秒，二者因保存先后略异。它们不是未来全量训练总耗时，也不代表从新文本开始的端到端推理速度。本地RTX3060 Laptop 6GB，无新模型下载；新增收费API为0次、0元。电费及机会成本未知，不能写成零计算成本。

默认系统、.gitignore及历史任务成果不变。用户已有docs/002提示词.txt删除和docs/写论文提示词.txt未跟踪改动不纳入本次提交。

本次检查仅验证暂停、恢复材料、现有工件及提交边界，见[pause_selfcheck.json](pause_selfcheck.json)；不替代完整任务自检，独立审计未执行。提交推送按用户本次明确指示执行，推送后保持暂停，不自动启动093。
