# 032 执行交接与独立审计入口

本文件由执行者整理，不是独立审计意见。最终执行状态以 RUN_STATUS.md、execution_status.json 和 completion_verification_001.json 为准。

## 本轮范围
沿用031的28名训练患者/2527条、12名已暴露确认患者/1148条；训练与确认患者不重叠。未开启reserved40，未新增收费API。
预训练NLI仅在本地处理冻结C48；模型来自 model_manifest.json 的固定revision。最终选择只用训练患者四折输出，确认标签在所有盲预测冻结后连接。

## 复查重点
- preparation_001：输入来源、患者分组、原始协议与环境版本。
- nli_001：54236组去重NLI输入、片段/同note两个粒度和大缓存指纹；大缓存位于 .local_models/032。
- training_001：运行前代码指纹、全部配置的折外结果、训练内选择及固定种子，不根据确认成绩改选。
- inference_001：五个家族的最终模型、盲预测、候选限制消融；零修正不能解释为NLI模块有效。
- analysis_001：统一002评价、031基线复现、作者/患者分层及候选/非候选修错与误伤。
- verification_001：从保存权重重新推理，不拟合、不重选配置；与原盲预测及logit对照。
- completion_verification_001.json / manifest.json：执行者补充完整性检查及产物指纹。

## 续接说明
上个会话结束时NLI仍在运行。续接保留52520组已写入缓存；长文本尾段批量16吞吐降低，恢复为批量4。旧运行日志及compute_override备份保留，未清空缓存。
准备快照与训练冻结快照并非同一时点；以training_001/freeze.json验证真正用于拟合的源码。报告脚本在训练前补充了批量调整说明。

## 安全重放
按 tasks/032_evidence_relation_correction/README.md 配置任务venv和research环境DLL路径；执行 verify032.py --output verification_review_001，输出目录必须全新。
不要为了审计重新调用下载器、Judge或覆盖历史任务输出。独立审计结论由独立审计者给出；本次不自动提交推送或启动033。
