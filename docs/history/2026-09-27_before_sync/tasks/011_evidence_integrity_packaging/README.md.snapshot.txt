# 011：证据完整性与局部结构恢复

用户交办：固定009/010的650条原命题、C48候选及真实rerank分数、structured Judge，比较A冻结C48、B基础修复、C额外结构恢复。主要C−B，另报B−A和C−A，区分恢复内容、预算挤占、原GT一致性和同输入波动。

**精简独立审计PASS，可冻结／结项。** 已完成650条离线检查，以及固定24条三臂各三轮诊断；预设继续门槛未通过，没有启动650条main。主要C−B三轮净正确数为−1/0/0，B−A为−2/0/0；停止当前规则组合扩展，不以B整体替换冻结C48。完整结论见[唯一中文主报告](../../outputs/011_evidence_integrity_packaging/report.md)。

正式规则为`packaging011.py`，输入见`offline_003`。前两版是收费前的语法/范围检查草稿，未用于推理；保留原文件和对应代码快照，未根据011模型结果调规则。B/C只复制同患者同note原文或description，禁止生成/猜测医学信息。每条件共同8000字符预算包括metadata/新增标题/正文，住院总头沿用009另计，每note2段、最多16段不变。

执行前固定范围、阶段预算、重复与继续门槛见[协议](../../outputs/011_evidence_integrity_packaging/execution_protocol_001.md)。全任务40元（pilot5、main35）保护，不按账号重置；实际195个有效请求/199次HTTP，usage估算¥1.2873834，无未知预留或收费预检。`main_preparation_001`是未执行的冻结方案，不是待补跑任务；不要运行live入口续做主比较。

代码分工：`prepare011.py`按已有候选和分数生成三臂；`build_jobs011.py`固定跨臂缓存和重复；`native_stage011.py`使用已审010执行器副本并加主阶段门槛；`score011.py`复用002/009评价并确定继续/停止；`diagnose_inputs011.py`与`diagnose_context011.py`分开保存正文和结构覆盖；`review011.py`保存24例完整材料，`case_notes.json`/`render_analysis011.py`生成8例人工阅读诊断。没有新建检索链路或修改共用评价。

在`research-verifact`环境从根目录离线重放，指定尚不存在的新目录：

```powershell
python -B tasks/011_evidence_integrity_packaging/verify011.py --output outputs/011_evidence_integrity_packaging/verification_audit_001
```

入口禁用socket网络，复建650条打包、已有pilot评价/门槛/案例，核对旧草稿对应代码快照及009/010文件，并运行160项测试。日常重放不因正常README/AGENTS/审计更新而阻塞；冻结输入、代码及回执仍严格检查。实际被审版本见[交审入口](../../outputs/011_evidence_integrity_packaging/audit_handoff.md)。交审后停止修改，执行者不写独立PASS。

当前状态：2026-09-15[精简独立审计PASS](../../reviews/011_evidence_integrity_packaging.md)，可按预设停止规则结项；main不启动。
