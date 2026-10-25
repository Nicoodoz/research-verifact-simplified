# 090 审计交接与私有材料边界

执行者自检与独立算式复核均不等于独立外部审计。正式结论见report.md；先核对最终`final_branch.json`、`final_construction_summary.json`、`sampling_audit.json`、`budget.json`与`main_freeze_summary.json`，不要把第一工程版当正式输入。

补充原生有效性核查：`raw_validity_check.json`独立复算8组原生共同有效指标，全部实际无raw fallback。冻结analysis中自然B/F的两个`raw_includes_fallback`描述性标志继承了旧core无效判断，应为false；更正位置及原因见`analysis_metadata_correction.json`，数字与预测没有变化。

## 冻结链

- 第一版：简化P/Q JSON接口和确定性归一，真实8例检查器测试；原始请求/回执及来源归一在私有目录。
- 第二且最后一版：source_repair_v2.json说明不同源事实/时点不能互相替代；构造器没有重采样，只对改变的两个P集合各检查一次。最终NS P补回U009。未读取090目标成绩调方法。
- 最终请求：四臂B/F4/P90/Q90，176自然＋66压力、968物理请求。active配置/ID/body SHA在第一份目标回答前冻结，按患者/ID与臂轮转发送。
- 自然抽样不读GT；压力仅按既定NS/NA与患者/ID规则抽样。与实际四例/PriorG及086 D患者隔离，均已暴露development。085冻结180条没有被取用。

## 重点复核

原四例claim/label/顺序与目标C48字节保持；B/F4系统和主模型参数沿087。P来源组不由可选排序字段否决，缺少信息约束不能转普通Q冒称P。空白引文唯一定位后仍复制原文，数值/单位/否定不模糊修复。P/Q独立调用，Q不因P失败取消，不为凑长度填弱相关段。

核对器raw错报/漏报与过滤后分开。固定8例软件文本测试都展示；临床例曾错报已保留U008，存在role/时间/必要性语义风险，不用合成测试通过认证医学安全。v2保守组拆分和一次具体补回的原始数据均可查。P/Q总长度接近但各槽不同，Q的NA还超过初始代理预算，不能冒称严格等token纯机制比较。

完整/raw自身共同有效/core共同有效分母分别检查；scores缺失不清空可解析raw，最终fallback预先同ID032 U2。归因先分invalid/fallback，再分raw和有效分数边界。六个固定比较全部报告，不择有利层/子组或把压力集并入自然PA。1000患者cluster bootstrap、三类指标和错误支持双分母完整。

预算40元含所有阶段/未知/在途，构造≤4元；成功回答不重发。原价估计忽略折扣，回执unknown预留不被当成免费。默认系统不变，无reserved、085、本地R1服务或权重下载。

## 公开复算与私有复查

公开文件含源码、ID/哈希、预测标签/分数、usage、指标和脱敏摘要。`predictions_public.jsonl`足以独立复算混淆矩阵与分类指标；完整原生推理内容、请求、来源原文/引句与私有患者材料不新增推送。

本机合法材料保存在既有忽略路径`outputs/replays/090_demo_constructor_repair_validation/`，文件清单及SHA见private_artifact_manifest.json。该目录不在Git交付中。来源/回执审计须合法取得相应私有材料；不能用公开摘要重造原回执，也不能在缺失时自动收费复跑。

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/test090.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/test_recovery090.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/090_demo_constructor_repair_validation/verify090.py
```

以上测试不联网。verify在合法完整本地材料上核对冻结及一次独立算式路径；重放不覆盖原报告。不要把construct/prepare/main当作审计命令；成功模型回答不得重发。中断恢复参见任务README，先确认旧进程/锁与原未知费用，不能删除账本重置预算。

完成正式报告、自检和推送后停止；仅在前两优先级完成后整理084—090地图和论文草稿，不自动091或恢复085。
