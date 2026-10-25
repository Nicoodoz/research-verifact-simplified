# 054 当前状态

054已完成，纯离线、0 API。使用052 T-S有效236条与053有效237条交叉source-target，模拟6种target prior、4种无标签batch size（60/120/240/480）、每条件500次重采样。

核心结论：BBSE能够在无目标标签时估计target类别比例，但当前DeepSeek自报label_scores不支持把估计prior自动塞回PriorG并期待分类稳定提升。

真实批次prior估计：052 BBSE L1=0.0312，053=0.0228；EM分别0.2189、0.1703。052上BBSE PriorG与Frozen PriorG性能相同；053上BBSE略差。

在5种shift×2个target的10个条件、n=480时，BBSE自动adaptation仅3/10提高PA、1/10提高MCC，平均ΔPA约-2.1pp、ΔMCC约-0.036。

更关键：即使使用Oracle真实target prior，也只有2/10提高PA、0/10提高MCC，平均ΔPA约-2.7pp、ΔMCC约-0.047。因此问题不只是prior估计误差，而是当前score并非可直接做Bayes prior correction的可靠calibrated posterior。

部署建议：Frozen PriorG作为默认；BBSE用于无标签shift monitoring/prevalence estimation；检测到明显shift后获取少量目标GT重新校准，不自动动态更新final prior。

source confusion condition number：052约5.94，053约4.41。T-S无效：052 4条、053 3条，主模拟只研究有效score池。

verification_001.json：62项PASS。正式报告见report.md。无reserved、无新增模型费用、未自动commit/push。
