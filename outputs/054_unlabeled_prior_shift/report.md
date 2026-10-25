# 054：PriorG under Unlabeled Label Shift

## 核心结论

054用052/053两批不重叠claim做纯离线label-shift模拟，固定T-S、G和PriorG公式，不搜索新bias/阈值。目标域没有标签时，用另一批有标签数据提供source confusion matrix；BBSE和EM只能读取目标域无标签预测/score。0 API。

最重要的结论不是“可以动态更新PriorG”，而是：

> **BBSE可以在无目标标签时估计新的类别比例，但当前DeepSeek label_scores不支持把这个估计prior自动塞回PriorG并期待分类性能稳定提高。默认冻结PriorG更稳。**

因此真实部署建议是：Frozen PriorG作为默认分类器；BBSE用于无标签shift监测/类别比例估计；若检测到明显shift，再获取少量目标域标签重新校准，而不是自动动态改prior。

## 1. 数据与模拟

- 052：T-S score有效236条，4条无效；
- 053：有效237条，3条无效；
- target=052时source confusion只由053估计，反之亦然；
- 6种target prior：source、90/5/5、70/15/15、60/20/20、60/30/10、60/10/30；
- adaptation batch n=60/120/240/480；
- 每个条件500次分层有放回重采样，evaluation batch固定240；
- 模拟保持P(score|Y)不变，只改变P(Y)，因此是纯label-shift构造。

## 2. 真实052/053批次：BBSE能估prior，但无需自动改分类器

真实有效池的GT比例：
- 052：S/NS/NA = 79.24 / 7.63 / 13.14%；
- 053：81.01 / 5.91 / 13.08%。

BBSE完全不读目标GT，估计为：
- 052：78.48 / 6.83 / 14.70%，L1 error **0.0312**；
- 053：81.64 / 6.42 / 11.94%，L1 error **0.0228**。

因此在与source prior接近的自然批次上，BBSE对prevalence的估计相当准确。

但把估计prior直接用于PriorG分类：
- 052：BBSE PriorG与Frozen PriorG逐条最终性能相同，PA 83.90%、MCC 0.5946、false-S 6；
- 053：Frozen为PA 83.54%、MCC 0.5596、false-S 8；BBSE变为83.12%、0.5428、false-S 9，略差。

EM则明显偏离真实prior：052 L1=0.2189，053 L1=0.1703；对应分类性能也明显下降。因此当前自报soft scores不适合直接承担无标签EM adaptation。

## 3. BBSE prior estimation本身是有效的

在5种真正偏离source prior的shift场景中，随着无标签batch增大，BBSE prior L1 error持续下降。两target pool、5种shift合计10个条件的平均L1：

| adaptation n | BBSE | EM |
|---:|---:|---:|
| 60 | 0.221 | 0.204 |
| 120 | 0.177 | 0.185 |
| 240 | 0.149 | 0.178 |
| 480 | **0.125** | 0.172 |

作为参照，如果完全冻结source prior而不估target prior，各shift的prior L1距离分别约为：high-S 0.192、S70 0.208、S60 0.408、NS-heavy 0.455、NA-heavy 0.408。

因此，特别在n=240–480后，BBSE确实从无标签hard predictions中恢复了大量prevalence shift信息。054并不是“BBSE估不出来”。

source confusion matrix的condition number约为4.41–5.94，有限但并不理想；NS类样本少且类间混淆明显，所以NS-heavy环境的prior估计仍较困难。

## 4. 关键反例：Oracle真实prior也不能保证分类更好

如果问题只在“BBSE估计有误”，那么给分类器Oracle真实target prior应该稳定改善。但结果不是这样。

在两个target pool × 5种shift = 10个条件中，不论adaptation batch size：
- Oracle PriorG平均只在 **2/10** 个条件提高PA；
- **0/10** 个条件提高MCC；
- 相对Frozen PriorG平均ΔPA约 **-2.7pp**，平均ΔMCC约 **-0.047**。

最典型的是high-S环境：Oracle prior提高S recall和PA，但同时压低NS/NA recall并增加false-S，MCC并未提高。相反，在S70、S60、NA-heavy等环境中，即使知道真实target prior，直接做prior correction也常降低PA/MCC。

这说明当前PriorG的三类score不是一个足够可靠、可直接按Bayes prior-shift公式重加权的calibrated posterior。真实prior是正确的环境信息，但把它机械作用到现有score geometry上不一定得到更好的分类边界。

## 5. 无标签自动adaptation的系统结果：不够稳

对5种shift、两个target pool，在n=480时：
- BBSE PriorG只在 **3/10** 个条件提高平均PA；
- 只在 **1/10** 个条件提高平均MCC；
- 10个条件平均ΔPA约 **-2.1pp**，平均ΔMCC约 **-0.036**。

BBSE有时能带来有意义的类别交换。例如053的NS-heavy场景，n=480时Frozen PriorG约PA 74.9%、MCC 0.563、NS recall 50.0%；BBSE约75.3%、0.576、NS recall 81.9%，同时false-S下降。但同样规则在052 NS-heavy场景却降低PA/MCC。这种跨pool不稳定性不支持自动部署。

因此，054支持“无标签估计target prevalence”，但**不支持无标签自动修改PriorG分类边界**。

## 6. 部署策略

当前最可防守的策略是：
1. **默认冻结T-S+PriorG。** 新环境没有标签时继续使用source-domain冻结版本；
2. **BBSE作为无标签shift monitor。** 用已有source标签得到confusion matrix，再从目标域hard predictions估计S/NS/NA prevalence；
3. 若BBSE显示target prior与source明显偏离，标记distribution shift，而不是自动更新final decision prior；
4. 获取一小批目标域人工GT后，再重新评价/校准G与prior correction；
5. 如果连P(score|Y)也改变，则label-shift方法本身不再成立，必须按更一般的domain shift处理。

这把“估计环境变化”和“修改分类器”拆开：前者054显示可行，后者当前证据不支持自动化。

## 7. Reviewer-facing answer

如果审稿人问“新环境prior变了但没有目标域标签怎么办”，054支持如下回答：

> PriorG在论文评价中使用冻结的source-domain prior，我们不假设该prior在所有部署环境中都恒定。若部署变化近似pure label shift，可用source labeled confusion matrix和target unlabeled predictions通过BBSE估计新的target class prevalence；在本研究的重采样实验中，BBSE prior error随无标签batch size增加而明显下降，并在真实052/053批次上达到L1约0.03和0.02。However, our LLM-reported label scores are not sufficiently calibrated for automatic Bayes-style prior correction: even Oracle target priors did not consistently improve classification. Therefore, unlabeled prior estimation is used as a shift-detection/monitoring mechanism rather than an automatic decision update. Material detected shift would trigger a small labeled target audit and recalibration.

这个回答的优点是没有声称“无标签就能自动适配一切”，同时证明我们并非完全无法处理新环境：prevalence变化可以无标签估计，但分类器更新需要额外校准证据。

## 8. 限制

- 054通过同一pool内按GT分层重采样严格构造pure label shift，因此不能代表真实医院间covariate/concept shift；
- source confusion只来自236/237条，特别是NS样本较少；
- `label_scores`是LLM自报分数，不是训练softmax；052/053 source诊断NLL分别约1.139和0.888，EM失败与概率校准不足一致；
- 主模拟只使用T-S score有效病例，真实系统的3–4/240格式失败仍按固定U2 fallback处理；
- 本任务用于robustness/reviewer analysis，不改变053冻结主系统。

054共0 API、0新增模型费用；verification 62项PASS。
