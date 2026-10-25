# 092 任务适配的临床证据核验模型

**完整结项（2026-09-27）。** 用户在AutoDL完成双臂五折训练后转回本地，后续收尾包含9065条OOF、一次条件融合、成本/类别/患者分析、原文部署检查、中文报告和完整稿。默认不变，不自动训练或093。

[正式报告](../../outputs/092_task_adapted_verifier/report.md) · [完整论文](../../outputs/092_task_adapted_verifier/manuscript_zh.md) · [全部指标](../../outputs/092_task_adapted_verifier/detailed_tables.md) · [完成指纹](../../outputs/092_task_adapted_verifier/completion.json) · [架构](../../outputs/092_task_adapted_verifier/architecture.md)。

## 数据与方法

100名患者9065有效atomic claim，五折患者分组OOF；每折64人梯度训练、16人选epoch、20人预测。全部标签使用依用户092明确授权，旧20/40/40仅保留历史角色，不改写036，也不称新holdout。模型独立读取claim+C48，无旧LLM分数；Frozen训练聚合/分类头，Fine额外更新DeBERTa顶部一层。只运行冻结的普通CE配置。

[原始授权](user_request.md)、[冻结协议](protocol.md)、[配置](config.json)、[唯一条件融合](optional_fusion_protocol.md)保持原样。研究结果提交ee8060a2b，之后的导航更新不等于修改冻结科学输入。

## 当前复查

日常直接读取上述成果。需要严格复算时，在ee8060a2b等对应冻结版本的隔离checkout携带合法私有材料，使用[统一环境](../../docs/RUN_ENVIRONMENT.md)。本次及未来导航维护会改变README等非科学输入的SHA；旧验证器如拒绝导航改动，使用历史版本，不改manifest放宽校验。

analyze092.py重建OOF总表，supplement092.py读取已有融合生成补表；write_report092.py/manuscript092.py/plots092.py生成文档与图，selfcheck092.py/final_check092.py会写检查JSON。这些不是无写入查看命令，不在当前正式输出目录默认重跑。当前只需查看原selfcheck与final_selfcheck结果。

prepare092.py/local_c48.py/cache092.py/train092.py是已完成的材料与训练生成步骤，不作为日常入口。continue092.py由completion.json阻止默认重训；完整重训需另行授权、隔离checkout和空的结果/模型目录。已有十组权重和OOF不需要再次训练即可用于分析。

fusion092.py已经完成唯一条件融合，不默认重拟合。其训练特征只来自同折64人中的B缓存，不能用其他折OOF造成间接泄漏；参数与训练ID保存在fusion_models.json，私有fusion_train_fold*.npz可回查。

## 部署与私有材料

infer092.py接受proposition_id/text/reference，载入指定fold的best.pt，从原文重新编码；不读取GT、LLM score或预存激活。已完成的12条时延/标签检查见deployment_benchmark.json，未再训练一个100人全量部署checkpoint。

.local_models/092保存原文、权重、优化器、token ID及缓存；activations是指向E:/Research-VeriFact-private/092/activations的junction，约49.7GB，属于原RTX3060缓存。云端RTX4090激活没有下载，不能将云端cache_manifest的时长或路径字符串当作本地缓存来源。

云端环境由outputs/092_task_adapted_verifier/092_autodl_environment.txt记录；原training_freeze_v3的Windows环境是本地准备历史。十组云权重/输入哈希核验、本地956条数值桥接和12条原文在线检查已经完成。GPU租金/完整远端命令日志未提供，不伪造补齐。

旧暂停标记为PAUSED_BY_USER.archived.md，旧报告及被云端替换的本地部分工件在local_pause_archive。权重、原文、私有回执不提交Git；不要凭未跟踪状态清理。最新项目规则见[AGENTS](../../AGENTS.md)，新研究仍须用户交办。
