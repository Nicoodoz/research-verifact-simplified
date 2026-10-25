# 022独立审计交接

**执行完成、按阶段A停止分支结束，待独立审计。** [主报告](report.md)；最终HEAD、工作区与文件SHA见`handoff_001.json`。不自称独立PASS，不自动commit/push。

## 核心复核点

1. 用户022计划与protocol_001在拟合/效果前冻结。原建议MCC正向、PA损失≤1pp已失败；补充结构门槛不是事后停止借口。代码仅一处JSON bool输出修复，原stageA_001与脚本保留。执行前历史汇总及一条schema探查评分暴露已在execution_notes披露，不声称全量历史结果盲。
2. 019 R0 650＋020 R0 879＝1529不同claim、16患者；020 R1另879条。4折固定患者哈希，作者/重复共同组。每次拟合只用其他12人的R0；没有R1训练或重复双权重。参数表保存全部训练评分request IDs。
3. 标准化是log(max(score/100,1e-6))，评分不是token logits；NS、NA、S平分；C退化(2,2)等于U2。G/C/M/V/T均同训练NLL、事前固定ridge及边界，无调参搜索。C两偏置没有人为强制排序；所有fit成功，无边界命中。
4. 正式stageA_002：R0 U2/C/G正确1285/1257/1257，MCC .580625/.564218/.564218，false-S90/69/69；R1 U2/C/G正确708/695/695，MCC .571084/.567901/.567901，false-S52/33/33。C/G全部2408标签逐条相同，但概率不同，不称数学等价。
5. 相对U2，R0 C救回10、伤害38、移除false-S21；R1救回6、伤害19、移除false-S19。不能把移除false-S全部算改对。完整类别/转移/患者/概率与混淆矩阵使用002输出；概率NLL/Brier/ECE是新增独立概率诊断，有简单公式测试。
6. R0主分析1529，R1仅879，R0_020同879用于稳定性；不能混为两轮均1529或2408独立样本。固定OOF后的bootstrap未重新嵌套拟合，解释其限制。
7. vector scaling概率改善但false-S明显增加；M小幅点估计变化不是预设winner。主候选失败后没有替换方案、调正则或用阿里云新输出救结果。
8. 022实际API为0，budget.attempts=[]；未知预留为0。模拟恢复测试不是实测扣费。阿里云0731当前可用性/价格尚未在022调用前核实，因为没有进入B；没有当前后端比较或Qwen迁移结论。

## 安全复核命令

仓库根目录、research-verifact环境。022验证器禁止socket连接且要求新目录；不运行旧019–021生成器、不加载模型。

```powershell
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/022_competition_aware_support_calibration/test022.py
& 'E:/miniconda3/envs/research-verifact/python.exe' -B -m unittest discover -s tests -p test_evaluation.py -q
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/022_competition_aware_support_calibration/verify022.py --output outputs/022_competition_aware_support_calibration/auditor_replay_001
```

已有verification_001：7224次独立乘法解码、24080行OOF、1529份证据来源、15个内容文件重放字节一致。12项022测试及15项002评价测试通过。冻结manifest校验准备/正式来源和代码，最终交审指纹补充文档与测试源码。README/AGENTS/API说明等现行导航允许变动，历史任务源码、回执、结果和GT保持。

审计须区分执行正确、方法门槛通过、概率质量和最终测试。022不是独立新患者确认，不重写019失败、020成功范围或021不等价结论。完成交接后停止修改本批正式成果；若有问题，追加修订快照。
