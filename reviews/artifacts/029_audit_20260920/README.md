# 029 独立审计附件

审计入口为 ../../029_semantic_information_gate.md。仅使用已有development数据，0 API，无新方法或参数搜索。

- handoff_snapshot.json / initial_check.json：原交审421项指纹。
- audited_files_sha256.json：415项冻结内容，排除六份现行导航；其原值仍在交审快照中。
- independent_check.py / independent_summary.json：不导入029实现；独立重建155条特征、3096个保存模型概率、患者隔离、阈值、357个混淆矩阵、406个LP工作点及两项主比较的2000次bootstrap与留一患者方向。
- replay_runner.py / replay_conda.log / compare_replay.py / replay_check.json：完整固定模型重训及逐字节对照。输出在忽略的outputs/replays/audit029_20260920_conda；运行元信息不要求一致。
- test_runner.py / tests.log：独立029环境8项测试；evaluation_tests.log：原research-verifact环境15项评价交叉验证。
- tests_initial_missing_irrcac.log：首次合并测试在029环境缺irrCAC，保留原失败；随后按各自依赖环境分开运行，未安装依赖。
- 初次直接调用029 python进程退出码1、无诊断输出，在忽略目录留下4份输入元信息；replay.log为空。使用项目已登记的conda run入口后完成正式审计重放，未改历史run或环境。
- pre_delivery_checks.json / delivery_checks.json：内容不变与提交检查；manifest.json为附件指纹。

复查使用 E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -B 后接 independent_check.py 的仓库路径。完整重放脚本要求全新输出目录；重跑前为脚本指定新目录，禁止覆盖现有审计或正式run。
