# 085A 任务入口

状态：**部署前离线准备完成；正式085未开始**。

- [用户原始要求](USER_REQUEST.md) · [冻结协议](protocol_predeploy.md) · [部署后交接](POST_DEPLOY_HANDOFF.md)
- `prepare085.py`：从084冻结材料生成GT盲180条队列与360条中立输入，已执行一次，使用`x`写入防覆盖。
- `fetch_tokenizer085.py`、`audit_lengths085.py`：官方固定revision只取tokenizer/配置并审计长度，已执行。
- `sagemaker_provider.py`：boto3凭据链、只读诊断、推理显式gate；当前只执行离线配置模式。
- `deferred_preflight085.py`：未来A虚构、B三个固定病例、C无GT parser冻结。现在未执行任何收费阶段。
- `parse_r1.py`：原生回执的thinking/final/verdict/scores等分层解析。
- `materialize_predictions085.py`：未来将360份原生回执以冻结parser转成GT盲预测JSONL；现在未运行。
- `evaluate085.py`：未来完整四臂统一评价入口，当前未运行。
- `selfcheck085.py`：离线检查，结果见[自检](../../outputs/085_r1_70b_model_swap/selfcheck.json)。
- [输出索引](../../outputs/085_r1_70b_model_swap/README.md) · [中文准备报告](../../outputs/085_r1_70b_model_swap/report_predeploy.md)

本任务没有推理API请求、没有reserved40、没有改`.gitignore`、没有commit/push。既有084结果文件只核对SHA，不重写。
