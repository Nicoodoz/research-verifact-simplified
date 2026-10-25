# 019有限语义深读：已实际阅读11例

事后选择lambda=1.5作为已登记网格中的机制示例；不是通过门槛的参数。每例完整读取原claim、C48全文、B/S完整输出。
共6名既用患者、22份模型输出。仅单次回答，没有稳定性结论或新增医生gold。原case_packets的21份U0材料只生成，不计作完整深读。

## 010_old6_N114（human/H）
GT为NS。C48记载5升液体后才转MICU；B接受S，但评分版本明确指出ED与ICU位置差异，U0正确NS。偏置又改S，属于相对U0的H，不是相对B新增的错误。

统一阈值会抹去已经识别出的关键事件地点差异。

**边界：** 未作新医学裁决；只确认原文顺序与输出差异，单次回答不能证明稳定。

[完整材料](010_old6_N114.md)；字面锚点见anchor_checks.json。

## 010_old6_N291（human/R）
原claim没有规定入院时或首次APAP水平；C48有后续水平11、停NAC的直接记录。B和S理由都额外聚焦初始或入院时未建议停药。U0为NS，lambda1.5改S，与原GT一致。

有目标时间被额外收紧的候选机制，不是仅仅相关药物共现。

**边界：** held与discontinued的临床语境仍需谨慎；偏置未重新推理，S原解释仍否定，不能据改对证明医学解释已修复。

[完整材料](010_old6_N291.md)；字面锚点见anchor_checks.json。

## 010_old6_N192（human/W）
GT为NA，B/U0为NS；C48包含住院治疗计划atorvastatin与CCU出院预期，两个完整回答均指出未明确出院用药单。lambda1.5改S，形成W：本来标签错，进一步变错误支持。

准确率净变化漏掉的错误支持代价有具体对应病例；住院用药不自动证实出院带药。

**边界：** 只讨论已给C48，不推断完整EHR没有记录，也不重判GT。

[完整材料](010_old6_N192.md)；字面锚点见anchor_checks.json。

## 010_old6_N374（human/correct_control）
完整C48有Echo类别、检查结果。B/S均判S且评分S100，所有lambda维持原GT正确。

直接检查结果支持命题的正常对照；无需阈值修复。

**边界：** 个例不代表全部正确样本机制或临床安全性。

[完整材料](010_old6_N374.md)；字面锚点见anchor_checks.json。

## 010_old6_N360（human/score_NS_loss）
GT为NS。C48有Heparin用药，但没有所给材料中的滴注启动说明。B判NS；S同样承认用药且否定滴注细节，却判NA并给S0。所有正偏置仍为NA。

加入评分后的NS/NA边界变化；不是放宽S能修复的差异。

**边界：** 不能用单次对照证明评分指令稳定导致错误；未对全EHR作证据不存在判断。

[完整材料](010_old6_N360.md)；字面锚点见anchor_checks.json。

## 010_old6_N503（human/unrescued）
GT为S。C48多次记录desaturation，也有bed alarm，但未读到所给包中的desaturation alarm声响直接记录。B判NS，S判NA且S评分0，网格不能救回。

具体事件修饰与可见证据范围问题；0分使有限正偏置无法触及该例。

**边界：** 不能据包内未见就断言全EHR缺证据、GT错误或检索必为原因；保留unknown。

[完整材料](010_old6_N503.md)；字面锚点见anchor_checks.json。

## 010_old6_N365（llm/H）
GT为NS。C48明确Amiodarone gtt停用但仍给口服；B和S都保留该区别并判NS，S30/NS70，lambda1.5改S。

与N291类似中等分数也可对应正确拒绝；统一偏置无法辨别真正过严与必要范围约束。

**边界：** 依照原标签与可见记录诊断，不提出新的临床治疗结论。

[完整材料](010_old6_N365.md)；字面锚点见anchor_checks.json。

## 010_old6_N367（llm/R）
GT为S。C48有DVT预防、活动受限和检查记录，B/S以没有明确high risk字样为由判NS；偏置改S符合GT。

有过度要求逐字风险等级的可能，也可能需要临床推断；不是所有救回都已有明确字面支持。

**边界：** 未以预防措施自行确立high risk医学gold；该救回的证据充分性仍unknown。

[完整材料](010_old6_N367.md)；字面锚点见anchor_checks.json。

## 010_old6_N066（llm/correct_control）
GT为S。C48有解释限液原因的护理记录，B/S均判S并给S100。患者仍索水不被误作没有宣教。

直接证据与范围适当解释的正确对照。

**边界：** 不是阈值带来的救回，也不据单例估计方法收益。

[完整材料](010_old6_N066.md)；字面锚点见anchor_checks.json。

## 010_old6_N334（llm/score_NS_loss）
原claim是lower-extremity CT。B区分躯干CT与下肢超声判NS；S的claim_summary改写成下肢静脉Doppler超声，继而给S100，与GT不符。lambda0已错，正偏置无法修复。

这是可见的核验目标改写，而非单纯S阈值保守。合法JSON和100分不能保证语义正确。

**边界：** 不把可见解释当模型内部机制证明；只确认目标文本和所评估对象不一致。

[完整材料](010_old6_N334.md)；字面锚点见anchor_checks.json。

## 010_old6_N529（llm/unrescued）
GT为S。C48含若干日期的抗生素记录，B/S把throughout解释为全住院期连续覆盖；S10/NS70，lambda1.5未救回，lambda2改S。

范围解释与包内时间覆盖不足并存；网格跨过边界不等于补齐证据或修复解释。

**边界：** 无法据这些片段确定全住院连续用药或判定GT错误，机制保留不确定。

[完整材料](010_old6_N529.md)；字面锚点见anchor_checks.json。
