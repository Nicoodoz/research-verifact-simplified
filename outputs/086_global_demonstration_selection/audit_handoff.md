# 086独立复核交接

执行者自检不等于独立审计。复核者先核对[收费前协议](../../tasks/086_global_demonstration_selection/protocol.md)和[冻结JSON](freeze.json)形成于任何086新回答之前，再按本目录冻结的SHA核对D/V/E患者清单、候选示例及五个完整有序组。`E_cases_blind.jsonl`不含GT；D*应只由`V_predictions.jsonl`、`V_utility.json`生成，其SHA绑定在`D_star_freeze.json`，之后的`E_jobs_freeze.json`绑定D*与E请求。

复核主线：

1. 检查085A [暂停记录](../../tasks/085_r1_70b_model_swap/PAUSED_BY_USER.md)及[资产盘点](085A_pause_inventory.json)，确认共享运行入口没有AWS默认路径。无需访问AWS。
2. 在原`research-verifact-029`环境，以`scripts/run_research.ps1`执行`verify_inputs086.py`、`test086.py`及结项后的`verify_results086.py`。注意`prepare086.py`使用新目录`x`模式，不要在现有冻结输出上重跑；`run086.py V/E`是收费入口，**审计时不要执行**。
3. 独立读取`attempts/*/request.json`、`receipt.json`，验证请求SHA、模型ID、complete body、same ID/arm唯一成功答案、HTTP0未知预留和按¥3/¥9原价usage计费。检查逻辑请求在V/E阶段共享一个¥30账本，无拆阶段结转。
4. 用公共`verifact_research.evaluation.evaluate/paired_compare`在同110 E ID重算raw/U0/U2/PriorG、患者bootstrap、false-S两分母、类别P/R/F1。E结果不得反向修改D*、E样本或五组。
5. 单列历史B/F4缓存、同批新F4、随机控制和作者原VeriFact；后者不是同Judge或同证据因果对照。核对12条B桥接与V旧/新F4波动。

首次E连接曾因历史082回退与032 U2在8个ID上不同而触发保护断言；核对后确认这8个ID的历史B/F4均核心有效，回退未参与历史预测。`analyze086.py`现保留历史回退与新032回退各自原值，仅在差异会影响历史无效病例时继续报错。原历史文件没有改动。

本仓库早期development和候选资料均已有曝光；这次患者级D/V/E隔离只适用于086流程。候选完整reference的教学充分性是既有筛查、没有新医生复标。新原生请求/回执含临床reference，只在仓库既有受控发布边界内处理；被忽略的`.local_models`缓存、AWS凭据或模型权重不入Git。
