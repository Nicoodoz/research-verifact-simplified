# 083 原生理由增量信息验证

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/083_native_rationale_information/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

083沿用082训练459条／14患者与患者外旧352＋新180条／22患者。实际原生回执F4/B各1015份，1015次新增收费调用只用于固定Qwen非thinking结构提取；主Judge、C48、F4、PriorG和默认系统均未改变。详情见[事前协议](protocol.md)及[中文总报告](../../outputs/083_native_rationale_information/report.md)。

执行顺序：`inventory083.py` → `prepare083.py` → `run083.py 3 3`预检（正式前三个请求）→ `run083.py 6`续跑 → `parse083.py` → `fit083.py` → `freeze_apply083.py` → `evaluate083.py` → `evaluate_B_aux083.py`（零API后验辅助）→ `cost083.py`、`label_exposure083.py` → `verify083.py <新outputs/replays目录>`。这是执行记录，**不要在正式路径重跑生成器**；其中`fit083.py`的joblib保存会覆盖同名文件。历史任务脚本仅导入只读解析和传输，不回写历史工件。`verify083.py`不拟合模型、不调用API。

完成结果：R细结构在532条上443正确、MCC0.4686、错误支持51；F4＋Frozen PriorG为447、0.5703、21；N/C/T/G也未形成可靠系统升级。当前版本停止，默认B＋Frozen PriorG不变。新增原价¥0.620007/20，执行者自检22,065项PASS；独立审计未执行。不使用reserved、不改`.gitignore`、不自动启动084。研究结项时未自动提交推送，用户后续单独授权推送083。
