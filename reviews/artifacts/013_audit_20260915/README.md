# 013快速独立审计证据

结论见[审计记录](../../013_multi_mechanism_screen.md)。check.py独立核算1436个原始回执的费用、主预测及停止结果，再禁网运行已有重放和174项测试；仅在内存中允许仓库外输出，未改变计算或校验。初版辅助脚本误设authority有created_utc字段，按实际改查各阶段冻结manifest与调用时序后完整执行，未改被审材料。

membership.py独立核对16项实际入选关系及原文，确认三处当前修正；不以引文存在替代成员关系。evidence.json、membership_checks.json是独立结果，replay_verification.json和tests.log为亲自运行记录。全部计算位于新的仓库外临时目录，没有API或密钥读取。重现时将脚本复制到新隔离目录，root为本次实际Windows仓库。finish.json记录审计索引更新后的冻结校验。
