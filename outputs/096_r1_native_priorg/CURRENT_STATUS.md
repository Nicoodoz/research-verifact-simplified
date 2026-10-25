096已完成AWQ-Marlin跨Judge与PriorG迁移验证：自然800条Original/V4 raw/R1 raw正确657/617/599；R1重新适配595，旧PriorG直接迁移616且与prior-only同标签。共同798条当前V4＋G正确664、MCC0.5802，R1-adapted594/0.4163。停止本轮适配，默认不变；1143 HTTP200、0重试，AutoDL用户已关机，按token新API0元、GPU租金未知。自检通过，独立审计未执行。

当前正式结果仅在valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k；旧READY_FOR_R1、live_v1与GPU_shutdown_handoff是保留的阶段快照。最新入口report.md；不自动恢复推理。
