# 阿里云当前使用说明（2026-09-28）

095已完成，新增目录价及未知预留¥95.769536/150；092历史新增API仍0。没有自动下一任务调用，095缺口/完整覆盖以其报告为准。主Judge仍直接阿里云DeepSeek，研究冻结模型deepseek-v4-flash-0731（T-S thinking-high）；可选Qwen同路。BGE仍默认硅基流动与冻结缓存。预算和恢复见[API政策](../API_POLICY.md)。

## 配置与换key

凭据在项目根.env.aliyun，不输出或提交。DASHSCOPE_API_KEY为鉴权，DASHSCOPE_BASE_URL为账号/地域适用的OpenAI兼容基础地址，DASHSCOPE_MODEL是通用默认；任务可用冻结模型ID覆盖。具体地址以本地合法配置为准，旧报告中的工作空间不保证新账号可用；文档同步不修改.env。

加载器调用时读取指定文件；已创建客户端不会自动刷新key。095在每个逻辑请求创建客户端，以冻结执行器为准，不应依赖修改通用默认来更改科学请求。更改默认MODEL不等于更改任务冻结模型。基础URL不重复添加/chat/completions。

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/run_aliyun.py check-config
~~~

这是本地格式检查，不证明在线权限或余额。真实预检要计入任务总预算；不为文档核对发送收费探针。

## 客户端与执行器

AliyunClient.send及CLI call仍为单次传输/留档层，不自动重试；研究执行器须落实预算内有限技术恢复。旧call_once/CLI默认40元是代码历史保护值，新任务显式传通常20元的有效上限。成功回答不重发；HTTP200核心无效按冻结研究规则，不因成绩差重试。

092未更换默认服务；085 Valdemardi是已完成的独立模型替换实验，不使R1成为默认Judge。[项目现状](../PROJECT_STATUS.md)与[全部任务](../TASK_INDEX.md)提供最新研究入口，016/071等运行回执仅解释历史。
