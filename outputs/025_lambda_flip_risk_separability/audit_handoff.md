# 025 独立审计交接

025执行和执行者自检完成，**未宣布独立审计PASS**。正式机器版本analysis_003，唯一主报告report.md。本轮停止。

## 研究判断及必要区分

E无稳定额外价值：024D SE R61/risk16，相对global确定性+5（CI[-2,29]）、混合包络+0.22（CI[-9.12,9.86]）；SE−S在同风险多5（CI跨0），SED−SD无正增量。停止当前E实现。

SD是额外正向线索：R64/risk10，相对完整global混合+15（CI[2.70,23.29]）；10/10去掉患者仍正；但Qwen不复现。**原完整门槛无winner**：SD历史复现项false源于019/020无跨模型D，不能评估，并非实测历史SD失败。gate_scope.json显式区分不可评价与反证；没有事后改原门槛，也不应以不可评价项否认已测得的OOF增量。只允许保留有限开发线索，不包装正式方法。

## 输入与范围

- preparation_001/source_manifest.json严格绑定019/020/024冻结输入、评分和预测。全部S评分合法，024使用879条S-only完整队列，与024 B缺一条无关。
- 019六人与020/024十人共16不同患者、1529不同claim，4166 score观察分组保留。没有reserved40病例读取，没有新API/费用，没有修改Judge/λ/证据。
- E特征只由冻结claim/reference和现存检索数值产生；禁用GT/author/患者ID作为特征。019缺3维rerank明细时恒0，不能把它的迁移当完整检索特征跨队列验证。
- 双模型probe根据用户本轮明确规则在025新建：peer.U2=S才保留主λ候选。D=46/5、Q=18/2与用户检查值独立一致；不是024已有审计方法或上界。

## 必审方法点

1. S/SE/SD/SED同一C=.1线性logistic，不搜索分类器/超参数。外层患者LOPO，内层训练患者LOPO只决定80%训练R阈值；所有标准化/系数/阈值排除测试患者。固定λ2只被gate否决，不重选λ。
2. 020 R1只能使用R0训练、排除同一个测试患者；R1不训练不选阈值。019→后10人的transfer绝不共享患者。fit_audit可逐项复核。
3. 完整global非负λ全部浮点切换直到全S；含0/2与历史锚点，不局限于旧7网格或[0,2]。deterministic阶梯和期望风险的随机混合上包络必须分别呈现，后者不是实现新λ或新随机方法。
4. 仅预先登记的嵌套阈值操作点用于继续门槛。OOF概率全曲线、raw score margin AUC仅描述；不得从曲线挑新winner。
5. R/H/W分别核算，risk=H+W、净正确=R−H；全队列指标调用002，不仅报告候选二分类。global基准用评价GT形成强事后参考，不能直接部署。
6. bootstrap为1000患者cluster、固定OOF输出条件区间，不含重训不确定性；不把同10患者的020/024当独立复制。不把廉价文本覆盖或系数解释当新医学gold。

## 两项工程修复（不是新方法版本）

- analysis_001完成数值计算后，decision.json因NumPy bool_不能序列化失败；原文件/原代码保持，serialization_repair_001登记Python bool转换。
- 自检识别布尔LOO权重在NumPy @运算中导致逻辑结果。frontier025_numeric仅把权重转float，模型/阈值/预测/主要指标/曲线/bootstrap未改；count_repair_001记录。analysis_002保持，正式analysis_003修正LOO及依赖门槛。13份不受影响内容逐字节一致。
- figures_001是视觉初稿（连线会让离散global看似可插值），figures_002改为明确阶梯和混合包络；数值不变，主报告只链接正式图。

## 自检与重放

- 8项单元测试通过，包括独立患者标签扰动不影响自己的OOF预测、内外层隔离、相同score精确浮点切换、完整λ覆盖、混合包络、单类训练退回、布尔权重计数。
- verify025：冻结来源/原执行代码/正式依赖hash；138个外层拟合的训练患者、标准化均值及概率；32组预测全队列002指标；R/H/W独立逐条计算；global混合包络由独立线性规划验证；所有LOO由逐条标量解码重算。
- verification_001/replay.json：15个核心输出在outputs/replays/025_self_replay_001重放逐字节一致；新目录不覆盖正式结果，网络connect被禁用。该replay目录沿既有gitignore排除，没有改.gitignore。
- 当前HEAD、未提交状态、全文件SHA见handoff.json；现行导航允许后续审计状态同步，正式协议/结果/源数据保持。

## 安全入口

```
python tasks/025_lambda_flip_risk_separability/verify025.py
python tasks/025_lambda_flip_risk_separability/analyze025_numeric.py --output outputs/replays/<new-directory>
```

分析和核查均离线，不需key。本任务不自动启动后续、重调λ或reserved test。
