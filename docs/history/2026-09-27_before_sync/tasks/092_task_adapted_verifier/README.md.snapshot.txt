# 092 任务适配的临床证据核验模型

**当前训练与分析已完成（2026-09-27）。** 用户在AutoDL完成五折双臂训练后转回本地，并明确授权收尾；完整OOF、一次条件融合、部署检查、中文报告与新完整论文稿已交付。默认B不变，不自动重训或启动093。旧暂停标记归档为PAUSED_BY_USER.archived.md；旧报告及被云端结果替换的本地部分工件在outputs/092_task_adapted_verifier/local_pause_archive保留。

本轮使用全部100名患者的9065条有效atomic claim，重新做患者分组OOF。历史20/40/40角色仍保留元数据，但不再用作本轮train/test界限；依据是用户092明确授权，不改写036历史。主对照只改变DeBERTa顶部一层是否由医生标签更新。

原始授权文本保存在[user_request.md](user_request.md)。正式结果形成后，当前checkout只做自检/复算；完整重训应在隔离checkout中保留旧公开结果作为对照、另建空的092输出及私有模型目录，避免覆盖冻结产物。恢复既有未完成运行用continue092.py，不重新执行材料准备。

## 运行

CPU准备/分析用 `pwsh -NoProfile -File scripts/run_research.ps1 tasks/092_task_adapted_verifier/prepare092.py`。

GPU步骤复用032任务环境；从仓库根运行以下命令，将最后脚本名依次换成 `local_c48.py`、`cache092.py`、`train092.py`：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -u tasks/092_task_adapted_verifier/local_c48.py
```

`folds092.py`固定划分，`baselines092.py`绑定缓存对照。`train092.py`默认运行全部5折×2臂；支持 `--fold 0 --family finetuned` 恢复单臂。已有complete及输入哈希吻合才跳过；未完成训练从优化器/RNG/epoch/cursor恢复。不要并发启动同一GPU阶段或多个相同runner。

`analyze092.py`在十组完整预测齐全后统一连接评价，主PA/MCC/AC1及配对区间调用仓库共享评价器，补充公式独立核算。`test092.py`检查窗口完整覆盖、原C48 packing重放、患者隔离和独立指标一致性。

## 部署推理

`infer092.py --checkpoint .local_models/092/finetuned_fold0/best.pt --input <private.jsonl> --output <private_predictions.jsonl>`。
输入每行只需 `proposition_id,text,reference`。不读取GT、LLM分数或PriorG，也不要求部署时已有activation缓存。OOF各患者使用对应折模型；不得拿一个包含该患者训练的fold权重冒充其OOF。

## 私有工件

`.local_models/092`存原文、模型、优化器及窗口token IDs；其中`activations`目录junction指向E盘NVMe的`E:/Research-VeriFact-private/092/activations`，存约49.5GB完整1024维底层token激活，保留D盘余量。已验证该逻辑路径被现有.gitignore覆盖，未修改.gitignore。私有文件不提交，公开仅ID、标签/预测、指标、源指纹及代码。所有模型均已有本地缓存，0收费API计划。

见[协议](protocol.md)、[配置](config.json)、[正式报告](../../outputs/092_task_adapted_verifier/report.md)、[新完整论文稿](../../outputs/092_task_adapted_verifier/manuscript_zh.md)。

## 已完成结果的复算

通过上述CPU wrapper依次运行analyze092.py、supplement092.py、write_report092.py、manuscript092.py、plots092.py、selfcheck092.py；这些步骤不训练、不调用收费API。它们读取现有完整预测与已存融合结果。最终文档/融合解码核查使用final_check092.py。test092.py依赖GPU环境中的torch/transformers，但测试本身不做真实训练。

融合已经运行，不默认再次拟合或重复生成特征。fusion_models.json保存每折参数与训练ID；fusion_predictions.jsonl保存结果；本地私有fusion_train_fold*.npz保存同折训练侧特征。若复现新增融合，必须遵守optional_fusion_protocol.md，并使用同折模型；不能将其他折OOF作为该折训练特征。

## 云端与本地数值来源

云端RTX4090环境由092_autodl_environment.txt记录，原training_freeze_v3中的RTX3060为本地准备历史。云端十组完整权重SHA及输入核对见cloud_training_manifest.json。云端激活未带回，现有E盘缓存是原本地RTX3060版本；融合训练特征明确使用该版本，956条云端外层标签桥接无差异但logit不逐字节相同。不要把新cache_manifest.json的云端计时套用于E盘旧缓存。完整从文本部署不依赖该缓存，入口infer092.py。

不需要恢复训练即可分析结果。私有权重、原文、优化器与缓存不推送；下载公开仓库本身不能恢复受许可限制的全部实验。AutoDL完整控制台日志和租金未提供，未伪造补齐。
