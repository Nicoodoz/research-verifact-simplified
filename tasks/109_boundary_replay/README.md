# 109 boundary_replay

[当前状态](CURRENT.md) · [固定方案](protocol.md) · [租卡交接](GPU_HANDOFF.md) · [准备报告](../../outputs/109_boundary_replay/preparation_report.md)。

本轮仅无卡准备，复用107 label_only既有模型/完整训练状态，准备“真实错误NS/NA＋当前正确近邻S＋已学正确保留”的单候选回放。CPU tests不表示9B涨点，没有真实困难样本已选完的主张。

- `prepare109.py`：复用106索引、排除标记与两512候选，构造受控294非S请求及可能S近邻，保留107原500评价。
- `select109.py`：只接受指定107检查点/原prompt的真实预测，固定64困难/64近邻正确S/64正确保留；不足停止。
- `run109.py`、`worker109.py`：未来用户租卡并明确授权后运行；原105 loss/104 prompt/107 checkpoint不改，full optimizer从50接续至74，固定24新步后评价500。
- `return109.py`：生成私有最终状态/原始预测归档，不上传或操作云平台。
- `analyze109.py`：未来CPU复算共同有效集、三类得失和患者配对，候选有信号才提出普通回放对照，不自动训练第二臂。
- `test_cpu109.py`、`test_resume109.py`：新增选样边界及tiny CPU接续测试；不加载9B、不初始化CUDA。

CPU准备用原032环境运行tokenizer/TF-IDF及tiny Torch；普通统计用research-verifact-029。不安装/升级现有环境。私有包包含临床正文和权重/optimizer，禁止提交GitHub；公开索引和CPU记录不是新临床标注或分类结果。旧实例/旧凭据不复用，不自动GPU或110。
