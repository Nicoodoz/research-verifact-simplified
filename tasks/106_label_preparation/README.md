# 106准备工件

[当前状态](CURRENT.md) · [一页决定](../../outputs/106_label_preparation/decision.md) · [证据报告](../../outputs/106_label_preparation/report.md) · [冻结协议](protocol.md) · [未来GPU交接](GPU_HANDOFF.md)。

唯一激活方案是同104原196条的标签目标诊断：固定105 mean控制，只新训练全局归一sum。普通/困难两个512数据包是本轮另行交付的未激活候选，不同时训练。源码不在import时连接云服务或启动目标模型。

## 工件分工

|用途|入口|
|---|---|
|现有105标签增量与固定源文索引|analysis106.py；semantic_A三份公开表与私有引用|
|3675池、512匹配候选与隔离|data106.py、data_token_lengths106.py；data_manifest.json、data_notes.md|
|固定claim-only患者OOF探针|probe106.py；probe_results.json|
|数学与实际标签编码|objectives106.py、tokenizer106.py；tokenizer_labels.json、tokenizer_objective_audit.json|
|唯一目标实现与小范围完整路径评分|loss106.py、worker106.py|
|无卡预检、授权/预算/恢复流程|run106.py、pack106.py|
|未来结果的CPU统一评价|evaluate106.py，显式bundle/results/output路径|
|准备自检与冻结|finalize106.py；final_selfcheck.json、preparation_freeze.json|

## 已有环境中的CPU检查

主环境：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/106_label_preparation/test_cpu106.py`。

数据核查：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/106_label_preparation/test_data106.py`。

小CPU张量使用已存在的032解释器并激活research：`E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -B tasks/106_label_preparation/test_torch106.py`。这不加载9B、不初始化CUDA，不安装或升级环境；029缺少torch/tokenizers不以强装解决。

生成器会写106准备工件；冻结后重建应在隔离副本或新输出快照进行，不覆盖正式冻结记录。验证历史SHA按相应历史快照；不要运行旧105 supervisor来“检查”106。临床全文与完整引句只在已确认服务条件或本地脚本内处理，不能进入公开web、GitHub或未确认云服务。

GPU执行只在未来明确新授权后按GPU_HANDOFF进行。本轮在READY_FOR_NEXT_GPU_DECISION停止，不自动启动、提交或推送。
