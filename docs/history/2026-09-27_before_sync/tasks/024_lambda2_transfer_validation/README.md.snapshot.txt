# 024 固定λ=2跨后端与跨模型迁移验证

**024当前：** 用户amendment_002核心字段口径优先。解析core024.py，执行run024_direct.py（同一阿里云端点，本任务进程直连），评价analyze024_core.py，安全离线核查verify024_core.py。HTTP200包括核心invalid均不重跑。[最新状态](CURRENT_STATUS.md)。下方初版入口只代表历史阶段。


正式协议：[protocol_001.md](../../outputs/024_lambda2_transfer_validation/protocol_001.md)。完整020队列879条，阿里云DeepSeek0731与Qwen3.8-27B，B/S各一次，λ仅0/2，任务80元累计上限。

`prepare024.py`一次性冻结；`run024.py --health --workers 4`发送4个正式接口验证请求，之后`run024.py`断点补齐未发送请求。`--retry-unanswered`仅用于保留旧记录后的无回答失败，HTTP200绝不重跑。执行器是真实收费入口，不作为离线重放使用。
