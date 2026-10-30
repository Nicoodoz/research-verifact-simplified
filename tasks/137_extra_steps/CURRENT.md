# 137 extra_steps：160初筛通过，补齐原500中

完整120 step369状态固定续训149步至518；模型、Adam、scheduler和RNG已回传，新增1192次呈现。32训练患者与20评价患者无交集，原GT、数据、顺序和loss不变。

同136输入的160条全部有效：MCC .5707→.5937，正确126→127，false-S17→15/57；S/NS/NA净−2/+6/−3。符合事前质量与风险信号，不能据此断言全量收益。

当前仅补原500缺失的340条，不重推160、不重复训练。若500仍有信号且预算允许，再补1317；否则保存结果结束当前版本。总窗口仍为23:40起GPU16元、API80元，API已用0，不关机、不释放。

[方案](PROTOCOL.md) · [初筛报告](../../outputs/137_extra_steps/report.md) · [训练完成](../../outputs/137_extra_steps/training_summary.json) · [实时进度](../../outputs/137_extra_steps/progress.md)
