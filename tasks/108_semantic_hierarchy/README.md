# 108语义分层与证据聚合

[当前状态](CURRENT.md) · [最终报告](../../outputs/108_semantic_hierarchy/final_report.md) · [完整指标](../../outputs/108_semantic_hierarchy/final_metrics.md) · [预写规则](protocol.md) · [资源接续](resource_amendment.md)。

flat_ce为普通三分类；hier_shared使用共享池化表示预测已涉及及条件支持，hier_pool使用阶段专用池化。联合概率恢复原S/NS/NA并argmax，NA不监督条件分支，原claim GT不赋给每窗。

CPU真实三头已完成，pool退化、shared按预写门槛进入GPU；4090同资料顶部层flat控制补齐后，shared综合退化，停止扩大。其余1317/固定第二种子/原文部署只准备未执行，不使用确认40、不自动109或默认升级。

prepare108.py准备患者索引；cpu108.py/model108.py运行冻结原CLS24头；gpu108.py执行顶部层及完整窗口，compare108.py复算固定500；extension108.py仅提供条件性后续准备/固定推理，本轮未触发；test_amp108.py覆盖真实遇到的AMP聚合回归。导入不会自动训练。临床原文、token、权重、optimizer和缓存只保存在私有目录。

首次A4000工程退出未收回日志，首次4090在正式训练前发现AMP归约类型错误并修正，均保留记录。新4090依用户指令未绑定额外自动关机任务，最终正常关机但不释放实例/磁盘。旧protocol中的A4000资源约束由本轮新用户授权及resource_amendment接续，研究方案不变。
