# 101：NS/NA定向复核

[正式协议](protocol.md) · [报告](../../outputs/101_nsna_review/report.md) · [全部数表](../../outputs/101_nsna_review/detailed_tables.md) · [病例解释](../../outputs/101_nsna_review/case_analysis.md)。

默认不自动续跑，不自动新搜索。收费入口runtime101.py只用于本次用户已授权、冻结并受30元总账约束的作业；成功请求不可重复。

## 结构

- common101.py：不可变工件及ID/哈希。
- prompts101.py：唯一提示、确定性解析与引用位置。
- prepare101.py：初始冻结与缓存盘点；原件保留，其endpoint默认错误由correct_cache101.py统一更正。
- correct_cache101.py：严格显式端点审核，保留原冻结、排除缺字段缓存，补5条原定基线。
- runtime101.py：单次最大上界事务预留、有限通信重试与完整回执；不按分类内容重试。
- stages101.py：开发格式检查、按首答触发及固定24重复清单；不按review质量选择。
- analyze101.py：完整阶段后统一评价和冻结判据；绝不替换重复首答。
- selfcheck101.py：身份/原GT/输入/费用/标签/评价与bootstrap重放，执行者自检。
- report101.py：从既有分析生成数表；人工病例解释另列。

主环境research-verifact-029，通过scripts/run_research.ps1执行。测试入口为test101.py，只有合成字符串和本地函数，不调用API。离线分析/自检在有合法私有材料时执行；历史哈希须保持，不以导航更新放宽冻结。临床正文和原生请求/回执只在.local_models/101_nsna_review。

## 主要解释边界

Supported预测集合固定，false-S不能下降；这是设计，不是通过实验新增的安全能力。真实S误拒也不能救回。NS是涉及但不完整支持，不要求明确矛盾；泛相关不代表特定断言被涉及，日期/剂量/状态不一致也不自动等于不同事件。所有患者已暴露；32开发与40确认隔离只属于本轮。

全NS/全NA是同触发集合的零API偏置诊断。nsna_plain和nsna_review同触发、同模型、同证据、同生成参数及调用数；输出任务和来源检验负担不同，均报告成本与fallback。回退保留基线，不能自动判NA。引用有效不认证医学真值。
