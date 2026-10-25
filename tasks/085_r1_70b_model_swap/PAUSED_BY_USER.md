# 085A 暂停记录（2026-09-26）

状态：`PREDEPLOY_READY_PAUSED_BY_USER`。用户决定暂缓DeepSeek-R1-Distill-Llama-70B与AWS路线，转向086全局固定四例选择。**暂停不是R1实验阴性、模型比较失败或已完成正式085。** 085A仍只有离线准备，未部署endpoint、未调用AWS控制面或推理端、未作R1性能评价。

## 原位保留与主入口边界

- [原协议](protocol_predeploy.md)、[原报告](../../outputs/085_r1_70b_model_swap/report_predeploy.md)、[原交接](POST_DEPLOY_HANDOFF.md)、provider adapter、deferred preflight、parser、正式评价框架、准备和自检脚本均保留原路径，不改冻结哈希。
- [原输出目录](../../outputs/085_r1_70b_model_swap/README.md)中的来源manifest、180条队列、360条中立输入、四例模板、tokenizer长度和2194项离线自检均保留。官方tokenizer四文件及独立venv留在既有被忽略的`.local_models/085a_r1_tokenizer`、`.local_models/085a_tokenizer_venv`；不下载权重。
- 085A先前仅改动`AGENTS.md`、根`README.md`和`docs/PROJECT_STATUS.md`的状态说明；没有改默认provider、阿里云客户端、环境启动器、共享导入、CI或自动预检。`sagemaker_provider.py`的离线默认模式无网络，`deferred_preflight085.py`缺`--allow-inference`只打印计划。086继续用原阿里云DeepSeek T-S及Frozen PriorG。
- 本地文件检查不能证明AWS云端不存在计费资源；本任务没有访问真实AWS控制面，也没有创建或清理云资源。

## 将来恢复须另行明确授权

先重新核对实际endpoint、区域、模型身份、部署成本、容器context与JumpStart sample inference code；按[原交接](POST_DEPLOY_HANDOFF.md)只提供非敏感endpoint元数据，本地通过AWS CLI profile/SSO认证。由用户另行授权后，才可执行`python tasks/085_r1_70b_model_swap/sagemaker_provider.py --live`只读诊断，以及部署适配后的`deferred_preflight085.py A/B --allow-inference`。原A/B/C和正式085仍须遵守其原协议；**本次086不执行上述命令**。
