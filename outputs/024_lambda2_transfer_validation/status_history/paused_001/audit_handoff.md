# 024 暂停交接：尚未达到正式效果审计条件

本文件仅交接实现、输入、服务和费用完整性；024研究验证尚未完成，不宣布独立审计PASS。

## 审查材料

- [协议](protocol_001.md)：先于任何024新模型回答冻结；全879条、两模型各B/S一次，λ仅0/2，80元累计。
- [准备manifest](preparation_001/manifest.json)：原020输入、019prompt/实现、执行代码及登记的SHA256；git HEAD代表024开始前版本，新任务文件尚未提交。
- preparation_001/jobs.jsonl含3516完整body；cohort.csv与020字节一致。Judge messages仅claim/reference，不含GT/author/source。
- attempts下44套request/receipt，预留先于发送写入，回执绑定请求hash，全部原始HTTP200/usage保持。
- [checkpoint_001/manifest.json](checkpoint_001/manifest.json)保存暂停时输入、代码、回执、费用状态指纹；[状态](checkpoint_001/status.json)列出格式异常。
- [主报告](report.md)不含不完整效果，也未对模型迁移作结论。

## 需要特别核查

1. 畸形输出内两个reason是否确实完全相同；旧019 parser确实拒绝，不混淆格式诊断和临床正确性。
2. 所有成功回答没有重跑，失败也未覆盖；没有新BGE或reserved40访问。
3. Snapshot0731采用官方忙时3/9价格，未错用普通别名1/2；Qwen3/12。0.642702是公开价估算，未核对账单。
4. prepare在新结果前完成，完整队列未改变；λ没有重新搜索。
5. `verify024.py`只读核对全部请求与020证据及原019prompt；`test024.py`和`test_closure024.py`共8项测试。
6. `analyze024.py`明确阻止不完整输出评价。该分析程序尚未经真实完整024数据端到端运行，不应宣称完整评价复现。

## 续跑

当前run024会因已有invalid终态拒绝续跑；不能删除该回执/改成未发送。若用户批准所述格式兼容修订，先新增修订记录及新解析适配实现，不回写原协议或原失败记录，再重用全部原回答。若不批准，则保持暂停。无论如何不动019–023冻结结果，不自动进入reserved test。
