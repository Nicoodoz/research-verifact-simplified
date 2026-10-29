# 109 boundary_replay

[最终报告](../../outputs/109_boundary_replay/final_report.md) · [完整指标](../../outputs/109_boundary_replay/comparison.json) · [当前状态](CURRENT.md) · [固定方案](protocol.md) · [无卡准备期交接（历史）](GPU_HANDOFF.md)。

本轮已完成：复用107 label_only完整状态，527条真实预测后固定选出64真错/64正确近S/64正确保留，192条续训24步，完整500评价全部有效。当前配方NA严重转判NS，自然/压力ΔMCC−0.1299/−0.4215，停止扩大。模型和完整状态已回传，用户确认11:35关机，GPU估算¥1.896、API0。

- `prepare109.py`：复用106索引、排除标记与两512候选，构造受控294非S请求及可能S近邻，保留107原500评价。
- `select109.py`：只接受指定107检查点/原prompt的真实预测，固定64困难/64近邻正确S/64正确保留；不足停止。
- `run109.py`、`worker109.py`：GPU执行须受用户新租卡授权及独立session约束；原105 loss/104 prompt/107 checkpoint不改，full optimizer从50接续至74，固定24新步后评价500。
- `return109.py`：生成私有最终状态/原始预测归档，不上传或操作云平台。
- `analyze109.py`：CPU复算共同有效集、三类得失和患者配对；本轮阴性，未补普通回放第二臂。
- `test_cpu109.py`、`test_resume109.py`：新增选样边界及tiny CPU接续测试；不加载9B、不初始化CUDA。

`summarize_mining109.py`汇总实际选样；`analyze_details109.py`复算作者/患者分层、风险区间及独立sklearn指标，无GPU或模型调用。

CPU准备用原032环境运行tokenizer/TF-IDF及tiny Torch；普通统计用research-verifact-029。不安装/升级现有环境。私有包包含临床正文和权重/optimizer，禁止提交GitHub；公开索引和CPU记录不是新临床标注或分类结果。旧实例/旧凭据不复用，不自动GPU或110。
