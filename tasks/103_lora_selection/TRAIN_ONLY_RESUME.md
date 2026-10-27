# 103仅训练阶段接续

用户2026-10-27最新授权：仅完成Qwen3.6-35B-A3B、Qwen3.5-9B、Qwen3.8-27B三款模型各512条LoRA。训练数据、患者角色与原始医生标签不变；不运行任何推理、评价或MCC计算。已完成的训练不得重跑。成果留在本次AutoDL持久目录，不回传大文件、不删除权重；全部完成后通知用户手动关机，原60元/8小时硬截止保护仍有效。

实例目录：`/root/autodl-tmp/verifact103`。独立环境`venv103`；数据`bundle/train512.jsonl`；模型`models/<model>`；各模型精确revision在`models/<model>/REVISION`及`bundle/model_metadata.json`。依赖实际锁在`results/installed_gpu_with_causal.lock`。三个模型优先使用已有BF16 LoRA；27B为稠密模型，55.56GB权重可在96GB上尝试原BF16配置，无须为QLoRA额外下载其他权重。

训练：`bash task/run_gpu_live103.sh --model qwen3.8-27b --phase train --limit 512`。其余模型替换名称。检查完成状态后才执行；有`training_done.json`且样本512、步骤64者不重跑。中断恢复加`--resume`，从`results/<model>/train/resume.json`指向的检查点读取adapter、optimizer与RNG。

配置：普通LoRA r16/alpha32，lr1e-4，microbatch1、累积8、单轮、梯度检查点，prompt/padding loss屏蔽，仅监督真实verdict。256与512保存；最终路径`results/<model>/train/checkpoint-512/`，含`adapter_model.safetensors`、`adapter_config.json`、`training_state.pt`。基础权重不得删除，须保留其固定revision、tokenizer和chat template；未来使用相同基础模型与最终adapter加载，不需要重新训练。

本轮不执行未来加载推理；成功检查仅确认512/64、实际LoRA更新、最终adapter/config及基础版本存在。日志`<model>_train.log`；资源、保存耗时、更新证据在`results/<model>/train/`。三者全部确认后写`results/three_training_complete.json`，停止队列并通知用户手动关机。

未来推理注意：在本次“仅训练”指令之前，35B适配器已成功加载，但batch8前向发生显存不足，旧日志保留。未来使用上述相同Unsloth/PEFT环境、固定基础权重并加载对应adapter，从batch1开始；不要默认复用旧batch8评价入口。本轮依用户要求不再进行推理验证。
