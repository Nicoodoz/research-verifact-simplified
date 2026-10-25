# 095 v3工程修订独立复核补记

此前[pricing_review.md](pricing_review.md)与初始失败测试原样保留。`/root/audit095`零API补读pricing095_v3、run095_v3、workflow、runtime_v3_note及冻结清单；未触碰运行中的A。

**此前两项具体缺口的修订核对通过。** [独立回归](runtime_v3_checks.json)由[check_runtime_v3.py](check_runtime_v3.py)产生：

- v3只有明确HTTP200且非unknown才交原计价函数；0/408/429/500/502/503/504、unknown和无效JSON全部保留最大bound，合成的“错误响应恰带usage”不再释放未知预留。成功同窗闲时仍按已核实目录价计算。
- baseline恢复从原冻结顺序筛除所有phase的同ID、同body成功B，包括core无效的HTTP200；不同body或非B臂不被误删。测试同时确认顺序保留。
- workflow现在查看所有阶段成功B，以请求UTC/rid确定最早者，不读取GT或正确性。复用时验证实际body SHA。若意外同ID出现不同B body，会断言停止而非静默混入；当前设计逐ID固定C48，不预计触发该冲突。
- 新wrapper仍要求不存在运行锁，使用原总账、原原子发送逻辑；每次恢复生成新清单与SHA，不覆盖初始队列、请求或回执。候选workflow调用v3，且保留候选科学冻结校验。
- 原workflow快照与旧v2清单记载SHA一致；新runtime冻结全部来源SHA通过。这里是版本化修订，不伪称旧v2清单指向当前workflow仍完全相同。

因此不再因这两项缺口阻止在旧baseline自然退出后使用v3。该结论不证明未来操作已经按入口执行：最终仍需核查真实请求重复数、未知账目、费率对账、各阶段覆盖及总额。正式A/D指标尚未复算，不能写095全任务审计PASS。
