# 108语义分层与证据聚合

[当前状态](CURRENT.md) · [冻结方案和继续规则](protocol.md) · [CPU报告](../../outputs/108_semantic_hierarchy/cpu_report.md) · [文献与反证](../../outputs/108_semantic_hierarchy/literature.md)

flat_ce为三类普通CE；hier_shared使用同一个池化向量分别预测已涉及和条件支持；hier_pool使用阶段专用池化。联合概率恢复原S/NS/NA再argmax，NA不训练条件支持分支；监督仍为原claim级医生GT，不赋给每窗。

prepare108.py准备授权患者索引，cpu108.py对原始预训练CLS24进行真实头训练和固定500评价，model108.py实现三臂；gpu108.py仅在绑定本轮筛查决定与预算/截止时间后更新原DeBERTa顶部一层；lifecycle108.py保留备份宽限和平台停机保护。实际入口参数见各脚本--help，导入不会自动开始训练。

本次CPU已选择hier_shared进入条件性GPU验证，pool停止；后续若有价值再补本轮同范围flat顶部对照。缓存头推理不代表完整原文系统时延。GPU私有包内有token和权重，不上传GitHub；公开目录仅代码、协议、指标与不含原文的预测元数据。
