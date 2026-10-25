# 事前机制探针在压力集中的跟踪（非额外实验）

全部使用现有canonical回执和真实selected_ids；无新调用、无新病例选择、无门槛更改。不是医学金标准。

|事前探针|实际操作与本轮结果|边界|
|---|---|---|
|N264字面patient主体|baseline S，contract NS，符合原NS；完整输出明确ASA和patient不同|同body的单位阶段contract曾NA，仍非原NS。两个阶段各用自己的答案，不挑较好结果。当前方向仅有局部主体纠错，不能抵消整体S损失|
|N395 Ortho会诊|selector将原C48候选中的note564631 [4504,5072)放入reference第3项，Judge引用Ortho并S；baseline NA|真实互补片段与标签改善同时出现，但单例不是总体收益。另一份同文note副本未必需同时保留|
|N526晚期HR|两份9月1日HR锚点从原C48不合资格变为wide有资格、rerank33/34，仍因character_cap未入最终包；所有臂NS|候选阶段的堵点解除，终端时间覆盖仍未恢复|
|N585目标日RLL|8月20护理段进入wide，rerank38、因character_cap仍未选；GT S但所有相关比较仍错|不是原EHR不存在；扩大候选不能保证目标段穿过末端选择|
|N642条件STRICT NPO|guard从原note471448的4376起补回if aspiration条件，24 Hour Events里的taking PO meds仍在；baseline/guard均NS|guard输出已承认条件，却改为不接受8月9日记录的24小时回顾。真实条件恢复不等于最终日期/状态判断已解决|

N264/N395/N642的上述相关完整新输出已另行阅读，N642补读实际变化/引用块。N526/N585的完整保存链路见[raw_traces.json](mechanism_analysis_001/raw_traces.json)；这里不声称对全部探针的六臂reference进行了额外全文重读。37个预定比较仍按原selection保存，这一跟踪不用于重新估计总体机制发生率。

程序复核还纠正了初稿三处解释：N305的ASA、N425的8月5日拔管、N644的吞咽试验本来就保留在两个条件中，不能因模型没引用或阅读界面没展开就算新增/丢失。现行[review_final_002](review_final_002/coverage.json)覆盖修正，87处字面锚点与16项实际成员检查分开保存；实验结果、请求、方法和门槛均未改变。
