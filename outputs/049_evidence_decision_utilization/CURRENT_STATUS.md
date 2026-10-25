# 049 当前状态

049 已完成 evidence decision utilization screen，并按预注册门槛停止；不进入confirmation。执行者verification PASS，独立审计未执行。

0 API阶段：当前U2在16条screen上9/16正确、false-S=2。明确反证否决A降到6/16，直接采用查证器B为5/16，严格Hard gate为5/16；都以减少false-S为代价大量误杀真Supported。

收费screen重新跑同期Fresh-B后，13/16满足本轮动态触发。完整16条路由结果：
- Fresh-U2 baseline：10/16正确，false-S=3。
- E（同证据只追加原文后用DeepSeek raw）：2/16，净−8，false-S=0。
- C（requirement→quote index，无relation）：5/16，净−5，false-S=0。
- R（带relation index）：3/16，净−7，false-S=0。
- E/C/R 的固定λ2辅助结果分别9/16、8/16、7/16。

C虽然高于E，但固定5条打乱requirement↔quote control与C标签5/5完全相同、正确数同为2/5，因此没有证据把C相对E的差异归因于“正确语义对齐”。6条repeat中B/C/R raw均0次变化，而B-U2有2/6变化，再次显示raw稳定、score边界漂移。

049 API共78次、78/78 HTTP200，usage估算约¥1.013049。verification 100项PASS。按用户授权，049弱信号后另立050研究重复scoring聚合；不修改049门槛救结果。
