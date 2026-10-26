# 018_verifact_gap_attribution

跨010/016已暴露队列的原VeriFact性能差距离线归因。任务执行完成、待独立审计；唯一必读[中文主报告](../../outputs/018_verifact_gap_attribution/report.md)。

## 边界

010六人650条＋016六人601条valid claims。主比较原发布rater121与各任务正式C48＋V4；010另用同期发布reference＋V4，016 Qwen仅敏感性。完整1251条机器评价，78例重点完整材料阅读（54方向性、24对照）；其余186条方向性机制unknown。剩余10开发患者、reserved test隔离，无新增API、训练或优化实验。

冻结[方案](../../outputs/018_verifact_gap_attribution/protocol_001.md)与[审计交接](../../outputs/018_verifact_gap_attribution/audit_handoff.md)。使用002统一评价；没有另写指标或修改GT。

## 代码与复核

环境`E:/miniconda3/envs/research-verifact/python.exe`，Windows pwsh，仓库根目录执行。复核目录必须不存在，不覆盖历史输出。

```powershell
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/018_verifact_gap_attribution/test018.py
& 'E:/miniconda3/envs/research-verifact/python.exe' -B -m unittest discover -s tests -p test_evaluation.py -v
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/018_verifact_gap_attribution/verify018.py --output outputs/018_verifact_gap_attribution/auditor_replay_001
```

验证器主动禁止socket连接，核对源manifest、1251条ID/GT/患者/预测、完整阅读清单、199个锚点及历史保护；重新调用002评价并重建诊断、打包和轨迹，比较95个内容文件。源码和原材料变化会失败；当前README/AGENTS/项目总览/审计索引及gitattributes为明确导航例外，不把文档同步当原实验变化。

| 文件 | 职责 |
|---|---|
| prepare018.py | 从冻结010/016/017及原发布对应ID建立机器台账、完整材料、块映射 |
| analyze018.py | 调用002评价/配对比较，作者/GT/患者四格与010桥接 |
| review018.py / view018.py | 固定优先病例，完整块去重阅读页；准备不等于已读 |
| notes_batch*.json / diagnose018.py | 执行者观察、未知范围、字面锚点及实际阅读覆盖 |
| trace018.py | 重建1251个C48并追溯9例11个字面锚点，非证据gold/recall |
| render018.py | 中文主报告、统计附录和病例索引 |
| verify018.py / test018.py | 离线重放、异常输入拒绝、历史保护与交审指纹 |

`prepare018.py`等生成器拒绝覆盖已有正式目录；请用上述验证入口，勿删除成果重建。阅读页块去重仅省略相同患者、文本与metadata完全一致的重复块，其原顺序和首次展示病例可回查；不做语义摘要替代全文。
