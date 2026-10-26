# 硅基流动客户端说明（2026-10-26）

研究完成至097，无自动调用待办。当前约定：Embedding／reranker使用Pro BGE并优先复用冻结缓存；Judge走阿里云，不要求先耗尽硅基流动。092本地补齐不证明其与API严格等价。费用、故障恢复以[API政策](../API_POLICY.md)为准。

## 配置

凭据只保存在受忽略的`.env.siliconflow_pool`，空模板见[keys.env.example](keys.env.example)。按SILICONFLOW_API_KEY_2、_3等读取账号；account_1已停用，不因旧Runner仍能加载它就重新启用。不要打印或提交密钥，也不为检查文档查询余额。

本地格式检查（不调用API）：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/run_siliconflow_pool.py check-keys
```

代码入口：[CLI](../../scripts/run_siliconflow_pool.py)、[客户端](../../src/verifact_research/inference/siliconflow_pool.py)。进程环境中的同名非空变量优先；运行进程不会因修改文件自动刷新账号。

## 实际能力与限制

| 行为 | 实现／要求 |
|---|---|
| 余额切换 | 明确无答案的402／30001后才切下一个账号，不把鉴权、超时或503当余额不足 |
| 成功回答 | HTTP200即留档，截断或内容不理想也不换key重发 |
| 其他错误 | 旧通用Runner会对429、401/403及部分未知状态暂停；新任务需在任务层实现已授权的有限技术恢复 |
| 费用 | 全任务累计，含未知及在途预留；默认20元，专项授权优先。reserved_budget_cny不是实际账单 |
| 恢复 | 校验请求清单、manifest和已有回执；不改文件以制造可重跑状态，不删除活动锁 |
| 模型和平台 | 不能因账号切换静默改变科学配置；旧实现没有通用跨平台调度器 |

新任务使用`run --requests <冻结清单> --output <新输出目录> --budget-cny <有效总上限> --workers <并发> --max-attempts <总尝试数>`；这只是接口说明，不是调用授权。单次上界、账号顺序和未知费用处理必须由任务协议确定。旧任务的40/80元上限不继承给新任务。

离线测试在[tests/test_siliconflow_pool.py](../../tests/test_siliconflow_pool.py)。历史402切换成功只能证明对应调用，不能证明所有错误路径或账号今天仍可用。旧完整说明在Git历史中保留。
