# 023 独立审计附件

结论见[审计记录](../../023_lambda_boundary_response_analysis.md)。

- handoff_snapshot.json / initial_check.json：原91项交审指纹及全部匹配记录。
- audited_files_sha256.json：83项冻结材料；8项当前导航的后续同步不回写原交审快照。
- independent_check.py / independent_summary.json：不导入023实现，独立核验评分、切换、各类曲线、历史锚点及022关系；同时校验7,625项历史文件。网络禁用。
- tests.log / tests_summary.json：10项023及15项002测试通过。
- replay_summary.json：审计者实际运行冻结verify023的结果；生成器原executor状态字样保留，独立结论见审计正文。
- figure1.png / figure2.png / figureS1.png：从实际PDF重新渲染并查看的审计图像，非原图替换。

仓库根目录、research-verifact环境可运行独立复算（先建立新的输出目录）：

~~~powershell
python -B reviews/artifacts/023_audit_20260919/independent_check.py outputs/replays/023_independent
~~~

该脚本只读研究材料，向指定目录写独立摘要。完整重放与环境说明见[复查入口](../../../docs/REPRODUCIBILITY.md)。
