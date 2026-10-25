# 050 当前状态

050 repeated scoring aggregation screen 已完成，无规则达到事前晋级门槛，因此58条患者隔离confirmation不执行。executor verification PASS；独立审计未执行。

Screen为4名development患者32条：16条历史raw-vs-U2冲突 + 16条仅按历史模型输出/固定hash选取的稳定control。每条完全相同DeepSeek scoring body独立调用6次，共192次HTTP200。

单轮U2正确数依次为20、22、21、18、21、21 /32，平均20.5；false-S依次4、3、4、3、4、3，平均3.5。32条中raw verdict跨6轮变化仅1条，但U2变化12条。

两个独立3-run triplet的聚合：
- Mean3：20/21正确，false-S 3/3，A-B标签一致84.38%；
- Median3：22/21正确，false-S 4/3，一致84.38%；
- LogMean3：20/21正确，false-S 3/3，一致81.25%；
- Vote3/Cons2：21/20正确，false-S 4/3，一致84.38%；
- Cons3：18/17正确，false-S 3/3，一致90.63%。

Median3平均正确21.5，比single-run平均20.5高1条，但两个triplet只有84.38%标签一致，未达到预注册稳定性和增益门槛。Cons3更稳定却明显损失正确数。无winner，不扩大。

冲突子集上single-run平均正确9.33/16，Median3两个triplet平均10.0；stable control上分别11.17/16与11.5。方向虽略正，但幅度小且不稳定，不能据此继续大批确认。

050新增DeepSeek调用192次，192/192 HTTP200，usage估算约¥2.402568 / screen cap ¥20。verification 205项PASS。结果入口：report.md、screen_analysis.json、screen_methods.csv、screen_item_diagnostics.csv、verification_001.json。
