# 阿里云百炼调用

现行入口：[当前配置与执行说明](CURRENT.md) · [API政策](../API_POLICY.md) · [研究执行原则](../RESEARCH_EXECUTION.md)。更新于2026-09-23；不再沿用初次接入016时的待执行状态和40元默认预算。

## 配置

在项目根目录`.env.aliyun`填写API key、适用工作空间的BASE_URL及默认MODEL。三个变量的作用、换key和模型覆盖行为见[当前说明](CURRENT.md#配置与换key)。[空模板](config.env.example)仅供填写格式参考；地址和模型必须核对，不在模板中放真实key。

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/run_aliyun.py check-config
```

该命令只作本地格式检查。需要真实可用性预检时计入任务预算，不重复进行无必要的探针调用。

## 客户端能力与任务责任

Python标准库客户端位于`src/verifact_research/inference/aliyun.py`，无需安装OpenAI SDK。`load_config`读取指定配置，`chat_body`构造默认非thinking请求，`AliyunClient.send`执行单次HTTP传输，`call_once`负责单次预算预留和留档。研究任务使用冻结的模型、thinking设置和请求体，不能把`chat_body`默认配置当作T-S配置。

单次命令`run_aliyun.py call`不自动重试、不换模型、不覆盖输出目录；任务执行器须在这一层之上实现有限技术重试、退避和断点恢复。未知计费和重试费用同时累计，成功回答不重发，HTTP200核心无效按研究协议处理。持续故障或费用超界才升级报告，详见现行API政策。

旧CLI默认`--task-cap-cny 40`、旧`call_once`默认40元仍保留在代码中；新任务须显式传当前预算，通常为`--task-cap-cny 20`或`task_cap_cny=20`。本次文档更新不声称执行器代码已修改。

初始单次传输的离线测试为`tests/test_aliyun.py`，不等于网络可靠性或任务自动恢复验证。016真实接入与071实际运行记录分别见[当前说明](CURRENT.md)的历史链接和[071报告](../../outputs/071_judge_icl_feasibility/report.md)。
