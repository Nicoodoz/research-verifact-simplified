# 082 标注锚点驱动的配置适配

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/082_anchor_configuration_adaptation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

082在固定C48、DeepSeek 0731 T-S及固定四示例F4的条件下，比较校准监督覆盖与配置共享。用户专项未优惠原价上限¥50，所有阶段共用；主训练采用079患者外14/22划分，新增评价从22名评价患者中的7名可用031冻结C48患者抽样。详见[事前协议](protocol.md)及[输出入口](../../outputs/082_anchor_configuration_adaptation/README.md)。

实施入口按顺序为`inventory082.py`、`prepare082.py`、`cache082.py`、`forecast082.py`、`fold_prior082.py`、`run082.py screen_B`、`select_boundary082.py`、`run082.py train_F4`、`collect_train082.py`、`label_use082.py`、`fit082.py`、`freeze_unweighted082.py`、`run082.py eval`、`prepare_apply082.py`、`analyze082.py`、`sensitivity082.py`、`analyze_unweighted082.py`、`core_valid082.py`、`run082.py repeat`、`analyze_repeat082.py`、`diagnostic_pairs082.py`、`plot082.py`。所有收费调用必须使用`run082.py`，每次调用前由该执行器检查全任务原价费用与在途上界。评分成功不因答案内容重发。`verify082.py <新输出目录>`为零API核验入口，不覆盖正式结果。实际权重敏感性补充记录见输出目录；`extract_report082.py`、`report_slices082.py`仅展示冻结结果。

旧任务冻结源码、工件、GT与默认系统均不修改。训练和评价材料使用真实医生标签，但目标GT不发送Judge。主输出及执行自检不等于独立审计；不使用reserved、不改`.gitignore`、不自动启动083。研究结项时未自动提交推送，用户后续单独授权推送082。

082已执行完成：合并532条中B＋G/F4＋G/F4＋配置修正分别正确438/447/453，但修正错误支持较当前18→33，新增180条相对F4＋G净正确0、错误支持+7。三族校准均未过训练风险约束，不升级默认。原价¥35.281902/50，执行者自检3750项PASS；详见[总报告](../../outputs/082_anchor_configuration_adaptation/report.md)。
