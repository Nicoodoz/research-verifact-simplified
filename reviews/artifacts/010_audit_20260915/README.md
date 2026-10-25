# 010 精简独立审计证据

结论见[审计记录](../../010_verifact_baseline_alignment.md)。check.py为另写的原生回执／Decimal费用／原标签与sklearn指标核对，随后在禁网下运行既有重放及150项测试。仅在内存中允许仓库外临时输出，未改来源或计算校验。evidence.json为独立结果，replay_verification.json与tests.log为亲自运行的输出。不存在新增模型调用。

初版辅助脚本误用旧任务的files键；按实际010清单files_sha256修正后完整执行。重现需将脚本复制到新的隔离临时目录；root为本次实际Windows仓库。临床重放正文未重复加入仓库。收尾检查见finish.json。
