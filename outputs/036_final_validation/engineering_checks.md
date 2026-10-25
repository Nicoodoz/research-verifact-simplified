# 执行期工程核验记录

## 环境

所有036进程均经`scripts/run_research.ps1`使用research-verifact-029；环境自检的NumPy/SciPy原生操作、L-BFGS-B及SLSQP正常。未安装新依赖、未修改主环境或029依赖。

## 已通过

- 发送前21项检查：正式参数、模型、prompt/body、费用上界、患者/claim训练隔离与重复名单等。
- 036单元测试7项：逐条复核完整3675条development的035推理、370候选Gate原实现、floor/tie、core/非core重复key、未知费用、指标单位、GT盲材料。
- 历史022校准测试12项：整数score穷举决策等价、正温度、梯度、训练隔离等；未更改历史测试。
- 036全部24个当时已建立的Python文件AST语法检查通过；后续新增文件也由实际入口执行检查。
- 纯合成36条的分析集成检查通过：人工置入B缺失和score缺失后，共同有效分母34、逐方法覆盖、全N敏感性、Gate回退及作者/概率/bootstrap导出均符合预期。全部假数据只保存在忽略的`outputs/replays/036_synthetic_integration_001`，不进入036临床结果或论文表。

## 已修复的预评价实现问题

组合导入时，检索与035都使用generic `common.py`，导致3个数值测试报AttributeError。在任何reserved评价前，新增`numerics036.py`以独立别名加载035模块及其依赖；7项测试随后全通过。旧/新指纹与详细记录在`evaluation_freeze_001`。原历史文件、科学定义、冻结模型均未修改。

## 未执行完的可选历史交叉库测试

尝试`run_research.ps1 -m unittest ...`被PowerShell命名参数绑定拒绝，无数据/调用副作用；改为直接`tests/test_evaluation.py`后，029环境缺少`irrCAC`，在导入阶段失败。`docs/RUN_ENVIRONMENT.md`已将带irrCAC的历史评价交叉测试归于原research-verifact环境。因此没有为重复已有交叉库验证而变更当前依赖，也没有把该套测试记为通过。036实际002指标路径不依赖irrCAC；其数值锚点和本轮指标/bootstrap由036安全重放核验。

以上均是执行者检查，不是独立审计。后续完整回执/C48/指标核验以`integrity_001`和`verification_001.json`为准。

## 执行完成后的核验与导出修正

- 3573条C48从原API向量、候选及rerank回执完整重建一致，8418个实际Judge请求与冻结模板/同一reference匹配。
- 4017条R0/R1盲预测先封存，再连接GT；原安全重放62215项检查PASS。2条R0核心无效按预设保留，158条非核心异常保留合法核心；全部12646次请求均一次收到HTTP200，没有重试。
- 费用初版accounting_001的金额正确，但rerank token列只读usage、未读供应商meta，错误显示0。accounting_002逐条核查4228份BGE回执，补正rerank输入36,731,639 tokens；总费用仍105.57673541元，原账本及全部科研结果不变。独立可重放`correct_accounting036.py --verify`。
- R0、R1和R0重复子集中，Joint_NLL与U4逐条标签一致；U2与U2_T/Task_T/Robust_T、U0与Std_T的指定标签等价检查通过。没有把MCC_T归入标签不变结论。跨轮比较两侧均为相同444个ID。
- figures_002在类别召回图增加已评价Std_V，展示其低NS召回；旧图、旧绘图源码保留，没有新增实验。
