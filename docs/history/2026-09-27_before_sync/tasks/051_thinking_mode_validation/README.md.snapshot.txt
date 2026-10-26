# 051：Thinking Mode and Scoring Interface Validation

051固定原C48/E0和DeepSeek-V4-Flash-0731，拆分thinking开关与是否要求label_scores两个因素。四条件为N-S、N-V、T-S、T-V；thinking固定high，不搜索强度。

48条balanced screen后T-V通过预注册risk lane，随后在另外8名development患者的96条balanced confirmation上完成四条件验证。T-V相对N-S+U2少12条false-S、净多3条正确，但N-V仍有最高正确数和MCC，因此T-V定位为低false-S风险工作点而非总体winner。

正式结果：`../../outputs/051_thinking_mode_validation/report.md`；当前状态：`CURRENT_STATUS.md`；executor verification：`verification_001.json`。独立审计未执行。
