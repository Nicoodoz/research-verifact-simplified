# 009 独立审计证据（2026-09-15）

结论请读 [独立审计记录](../../009_retrieval_baselines.md)。这里保存机器证据，不增加第二份必读研究报告。

- `handoff.json`：被审交审清单原样副本，3,114 个文件；不是审计后重新生成的执行清单。
- `independent_checks.py` / `independent_results.json`：审计者另写的原始回执、Decimal 费用核算、预测与 sklearn 指标、候选／真实分数、缓存、时间顺序、重复、分数漂移和干预集合检查。
- `additional_checks.py` / `additional_results.json`：独立引用／排名与选例核对，隔离副本中的回执、请求篡改和缺分数／跨患者负向检查。初版辅助脚本曾误用不存在的 review_002/index.csv，已按实际 packets.jsonl 修正并完整运行；该路径假设错误不是执行成果问题。
- `run_replay.py` / `replay_verification.json` / `tests.log`：亲自运行既有重放和 143 项测试；只在内存中更改输出位置断言，其余检查保持。重放 JSON 中原有 self_check_not_independent_audit 字段保留；独立审计还依据上述另写检查、源码审阅和病例阅读。
- `read_cases.py`：用于定向显示完整输出／证据和执行者观察的辅助读取脚本；阅读范围见独立审计记录。
- `audit_version.json`：HEAD、远端、原修改清单及最终文件指纹。

实际使用 Conda `research-verifact`；所有计算脚本在 socket 禁网保护下执行。输出位置为仓库外 `%TEMP%/verifact_009_audit_mewu89kp`。仓库内未保存重放出的临床正文副本，也未修改任何执行成果。需重现时，把脚本及 handoff.json 复制到新的隔离临时目录再运行，保留原输出不覆盖；脚本中的 root 指向本次实际 Windows 仓库路径。

109 个非 manifest 内容文件重放一致；这不等于审计者逐字阅读全部临床案例。相关文献审查为定向范围，未新增医学标注或模型调用。

收尾追加：`post_review_replay.json` 与 `replay_after_review_update.py` 记录正常审计索引更新后，正式重放入口在工作区白名单断言失败的实际复现。失败前 109 个内容文件再次重建一致、3,114 个交审文件未变。最终状态为有条件通过、需修正重放入口；以审计记录末尾为准。
