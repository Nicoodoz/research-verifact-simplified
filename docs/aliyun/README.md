# 当前Judge接入（2026-10-26）

用户已授权启用千问AI官方端点，新Key已配置在根目录受忽略的.env.aliyun。默认模型为deepseek-v4-flash-0731；通用chat_body默认开启thinking-high。具体配置和测试证据见[CURRENT](CURRENT.md)，无密钥模板见[config.env.example](config.env.example)。

客户端仍使用src/verifact_research/inference/aliyun.py和scripts/run_aliyun.py，不需要OpenAI SDK。load_config读取指定文件，环境变量不会覆盖它；已创建客户端不会自动刷新Key。AliyunClient.send只负责一次传输，call_once提供预算预留及回执，任务执行器负责有限重试和恢复。

正式实验必须显式构造冻结的模型、prompt、max_tokens和格式契约。chat_body的2048输出上限是通用默认，不替换历史实验的8192；可显式enable_thinking=False做非思考测试。旧请求不会因配置切换自动重发。

旧CLI/call_once默认40元保护值仍在实现中，新任务须显式传有效任务上限，通常20元。密钥不进入代码、回执或Git；换账号不重置任务预算。最新配置启用仅做离线验证，不额外调用API。
