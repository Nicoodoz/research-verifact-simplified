# 051 独立审计交接

状态：preflight、screen、semantic diagnostics、patient-isolated confirmation均完成；executor verification PASS；独立审计未执行。

审计重点：
1. 16名患者固定hash分8 screen / 8 confirmation，balanced sampling仅用GT做预声明分层且GT未进入API；
2. 四条件请求只改变thinking与scoring接口，T条件固定enable_thinking=true、reasoning_effort=high、max_tokens=8192；
3. screen criteria与24条semantic diagnostics在科学screen前冻结，T-V按risk lane晋级后才构建confirmation jobs；
4. confirmation 384个jobs与冻结hash、请求/receipt一一绑定，652/652 HTTP200且无内容驱动重跑；
5. T-V vs N-S+U2、T-V vs N-V、T-S raw vs N-S raw配对统计及患者方向；
6. T-V citation结构核查，区分同次label/reason生成与真正grounding正确；
7. 费用、thinking reasoning usage、唯一T-S核心JSON invalid的missing-as-error处理。

主要入口：`freeze.json`、`screen_freeze.json`、`screen_analysis.json`、`screen_decision.json`、`confirmation_freeze.json`、`confirmation_analysis.json`、`confirmation_bootstrap.json`、`verification_001.json`、`report.md`。

执行备注：冻结jobs/requests/receipts是科学条件的source of truth。任务执行后对common051.py做过一次重复helper定义清理，不改变任何已发送body或保存response；verification逐request绑定到冻结job。
