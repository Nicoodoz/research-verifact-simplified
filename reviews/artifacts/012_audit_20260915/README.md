# 012 独立审计证据（2026-09-15）

结论及范围以[独立审计记录](../../012_comparative_error_diagnosis.md)为准，不增加第二份必读研究报告。

- `independent.py` / `independent_results.json`：审计者另写，未导入012实现；直接连接release、010 canonical原生回执和body，重算三组指标/错误并集、选样和7,861个C48块的否定词风险，独立核对67处字面引用。
- `trace_checks.py` / `raw_trace_checks.json`：独立重建N086/N395/N526等关键原note至候选、重排和最终reference的位置，不伪造原系统上游日志。
- `replay.py` / `replay_verification.json` / `tests.log`：亲自断网运行165项测试与45个内容文件重放；仅在内存中放开输出位置，其他计算和校验未改变。
- `finish_checks.py` / `finish_checks.json`：隔离输入/代码/结果/跨患者负向检查；核对阅读缓存规范化空白的7组非逐字节相同情况，原始reference不变。
- `read012.py`：定向输出完整生成和来源材料的读取辅助；实际阅读范围见审计记录，不能由脚本存在推断全部病例已深读。
- `version.json`：交审版本154个文件匹配；`publication.json`记录独立结论形成后的当前状态文档更新。

全部计算位于仓库外临时目录 `verifact012_audit_20260915`，Conda research-verifact、socket禁网；没有新增API、密钥读取、新患者或医生标注。重现时复制脚本至新临时目录，保留已有目录不覆盖；root为本次实际D:/Research-VeriFact。交审快照对当前文档的哈希是历史版本，不是永久计算依赖。原始临床重放全文不在本目录重复保存。
