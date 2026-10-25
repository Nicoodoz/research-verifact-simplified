# 016独立审计交接

本次交审对象：`completion_002/report.md`及其机器结果。执行者未宣布独立审计PASS。

## 必核范围

1. 原601条队列与003第25–30名开发患者，完整C48与015 evidence_only原版prompt；无新患者或隐藏Judge字段。
2. 跨供应商／时段偏差按调用前登记披露：V4旧601全部保留；Qwen硅基流动127＋阿里云474（含原测试1条），不重生成成功回答。
3. 全部V4/Qwen分歧的两臂覆盖、原ordinary repeat完整body相等、候选答案不进入review、共同标签原样保留。
4. `analysis_001/`002指标、配对患者bootstrap、类别／患者代价、原gate代码，以及部署调用／成本对照。
5. 016从最早检索开始跨所有账号、供应商、失败和测试的累计费用；未知预留不释放。`attempts.csv`每个回执可回查。
6. 断网重放与真正Windows检出；正常顶层导航变化不阻断旧历史，而请求、代码、回执、协议和结果须严格。

## 离线入口

`python -B tasks/016_disagreement_triggered_review_validation/verify_completion016.py --output <全新验证目录>`

`python -B tasks/016_disagreement_triggered_review_validation/analyze_completion016.py --output <全新分析目录>`

`python -B -m unittest discover -s tests -p test*016.py`

`python -B -m unittest discover -s tests -p test_aliyun.py`

日常验证不需密钥或网络。既有verification_001不覆盖，审计使用新的目录。本轮complete016续跑入口在completion_002/analysis_001存在后禁止新增发送。

handoff_001.json记录实际HEAD、未提交状态、内容与代码指纹。顶层README/AGENTS/reviews索引及.gitattributes的哈希单列为可变导航快照，不作为计算重放依赖；历史016自己的README和所有报告仍严格冻结。独立审计期间停止改动被审成果。
