# 107 GPU执行完成

两臂正式训练均50步、392次消费，原196条重复两轮；两臂各500条首次评价回执完整保存。所有训练步ID/顺序/尾批缩放与原计划一致，全部评价输入token SHA与固定batch2的250组核对通过。没有旧预测复用或辅助头推理投票。

真实方法实现已核验：两臂从同原9B初始化，初始LoRA/RNG SHA相同；辅助单独反向实际进入248个LoRA_B张量；未来答案与prompt-only测试均0差异；最长完整训练含Adam状态峰值约27.05GB，batch2最长输入+384输出资源检查通过。正式训练峰值约26.87GB，正式评价峰值约24.10GB。原环境复用，5090不兼容的旧xformers路径由Unsloth自动禁用，未升级/重装依赖。恢复状态逐字节正确；下一步BF16反向数值不确定性及修正见[工程更正](execution_amendment.md)，不声称逐位重训一致。

正式步骤累计：label_only训练932.40秒（含保存44.83秒），评价生成487.29秒；support_aux训练934.07秒（含保存45.10秒），评价生成483.81秒。时间不是分类收益。

本地完整备份960,727,194 bytes，543个文件SHA核验通过；包含两臂最终adapter、支持性head及完整optimizer/scheduler/RNG训练状态，原始预测和运行日志。基础9B权重未另下载到本地，仍依赖原镜像保留底座或同SHA原权重。临床正文、完整回执、权重/检查点和凭据不公开。

当前：**用户已确认关机，待CPU离线统计**。费用状态见[cost_status](cost_status.json)，API0。阶段三只在停止GPU计费后使用CPU计算共同有效ID、三类得失和配对区间；当前不依据训练loss或少量案例宣称方法有效。GPU阶段完整允许公开工件归档本仓库，精简仓库保留关键成果。

[运行资源](resources.json) · [GPU检查](gpu_gate.json) · [整轮预算](whole_run_budget_gate.json) · [本地备份](backup_receipt.json) · [执行者自检](execution_selfcheck.json)。
