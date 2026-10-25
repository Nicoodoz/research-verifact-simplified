# 阿里云客户端与研究路由

更新至092结项（2026-09-27）。[当前配置](CURRENT.md) · [API政策](../API_POLICY.md) · [执行原则](../RESEARCH_EXECUTION.md)。

主Judge直接阿里云，不等待硅基流动全池耗尽。凭据仅保存在.env.aliyun；[空模板](config.env.example)不代表任何账号当前在线权限。

Python标准库客户端在src/verifact_research/inference/aliyun.py，不需要OpenAI SDK。load_config读取指定配置；chat_body的默认非thinking请求不等于当前T-S实验请求；AliyunClient.send执行一次HTTP，call_once提供单次预算预留和留档。

旧CLI/call_once默认40元仍在实现中，新任务必须显式给有效上限，通常20元。有限重试/退避/断点恢复由研究执行器负责，预算包含未知预留，成功回答不重复。本次不改变客户端实现或运行任何在线探针。

本地配置检查命令见CURRENT.md。研究正式执行必须使用具体任务冻结模型和参数；旧示例和历史runner不是新任务授权。
