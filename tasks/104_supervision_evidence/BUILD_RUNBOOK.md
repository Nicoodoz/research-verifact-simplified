# 104配对构建与CPU接口

本工具不训练、不加载模型权重、不调用API。真实盲审台账先完整封存，再连接原GT；引用位置只能证明字面来源，不能替代语义核查。

## 顺序

1. 首审全部完成后，运行只读结构检查：

```powershell
python -B tasks/104_supervision_evidence/build104.py --validate-only
```

`--dry-run`同为只读检查，不打开gt_key；`--allow-partial`仅供工程盘点，不能用于冻结。以`assignment.json`核对实际reviewer，不从文件名或mod3推断角色。每ID恰好一份首审，必须完整阅读并明确记录`full_reference_read=true`。

2. 保存三份首审原件副本及SHA：

```powershell
python -B tasks/104_supervision_evidence/build104.py --freeze-blind
```

私有快照在`blind_review_freeze/`，公开`blind_review_freeze.json`仅给指纹。首审文件、assignment或盲包之后变化会阻止GT连接；不能修改旧稿来贴合GT。

3. 连接原GT，输出初步候选与隔离清单：

```powershell
python -B tasks/104_supervision_evidence/build104.py --build
```

仅生成私有`candidate_paired/label_only.jsonl`和`candidate_paired/evidence_brief.jsonl`；这不是已独立语义通过的最终训练集。初步分歧保留，独立NA而原GT为S/NS优先记`reference_gap`，其他未解分歧记`unresolved`。字数仅统计，不靠凑字数或关键词自动认证关系。

初始GT连接另存不可替换的`review_joined_initial.jsonl`，candidate manifest和教师队列绑定该文件。`review_joined.jsonl`是当前态，后续最终修订不会覆盖initial，也不会改变原candidate来源指纹。

4. 固定质量复核后，root以独立决策文件明确接纳/隔离，并留修订理由与复核身份：

```powershell
python -B tasks/104_supervision_evidence/build104.py --build --decisions .local_models/104_supervision_evidence/final_decisions.jsonl
```

决策每条至少含`id`、`reviewer`、`revision_reason`、`final_status`（`gt_explained`/`reference_gap`/`unresolved`）、`quality_approved`；可显式修订`evidence_quotes`、`relation`、`na_anchor`。首审与GT不同而拟接纳的，另须记录`independent_semantic_audit`，不能仅据GT改写。原独立verdict与首稿SHA仍保留。未明确接纳的候选不会自动进入最终`paired/`。

教师核查后的答案需显式传入最终decision；来源通过`supervision_metadata`白名单（teacher_review/relation_origin/teacher_semantic_reviewed）对称保留在两臂，不能改变ID、GT、原claim/reference或prompt。

## 数据接口

- 两臂逐行保持同ID、患者、作者、原GT、claim、reference、原训练顺序、messages及证据元数据，仅`answer`/`answer_text`变化。
- `answer`为JSON字符串，`answer_text`是相同字符串。`training104.encode_lists`直接监督这段答案及EOS，不能继续调用103固定GT-only答案的旧编码器。
- 证据偏移位于`metadata.evidence_spans`。每引句保存`quote_sha256`及全部`occurrences`；重复引句不得任意选首处。显示编号不是原note ID，原文未发布note ID则为null。
- `training104.messages`是唯一prompt构造入口；输入JSON只有text/reference，不含GT或审查状态。关系短说明是机器辅助监督，不是新增医生gold或完整思维链。

## 最小验证与实际tokenizer

```powershell
python -B tasks/104_supervision_evidence/test_build104.py
python -B tasks/104_supervision_evidence/test_training104.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/104_supervision_evidence/check_interface_cpu104.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/104_supervision_evidence/tokenize104.py --pair-dir .local_models/104_supervision_evidence/paired
```

CPU主环境当前未安装tokenizers；本轮复用既有tokenizer-only环境，不升级或重装。`check_interface_cpu104.py`只使用纯合成工程文本，检查真实固定9B tokenizer、模板、两臂共享prompt、答案/EOS监督和prompt/padding屏蔽，不读真实盲审或连接GT。真实数据长度统计在最终配对包形成后执行；候选长度盘点需显式传`--pair-dir .../candidate_paired`，不会冒充最终集。

## 结项后的离线重放

104已完成64次固定请求，不需要再次调用API。完整原回执、SQLite账本、教师decision和post_audit_decisions均在私有目录。离线重建使用：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/104_supervision_evidence/api104.py export
python -B tasks/104_supervision_evidence/finalize104.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/104_supervision_evidence/tokenize104.py
python -B tasks/104_supervision_evidence/analyze104.py
python -B tasks/104_supervision_evidence/cost_stats104.py
python -B tasks/104_supervision_evidence/case_findings104.py
python -B tasks/104_supervision_evidence/selfcheck104.py
python -B tasks/104_supervision_evidence/write_report104.py
```

`export`只读取和对账既有回执；`finalize`承接teacher_checked版本，对固定质量核查中的flagged条目要求显式语义决定，不救回原盲审分歧。本次最终196条，两个NS另行隔离，NA引用补完整句；原稿不覆盖。重放完成会更新当前派生工件的创建时间，原始盲审和API冻结材料必须仍通过SHA校验。不要为重放重做首审、生成新教师解释、删除账本或重新选样。

完整工程测试在现有CPU/API环境执行：

```powershell
& ./scripts/run_research.ps1 @('-m','unittest','discover','-s','tasks/104_supervision_evidence','-p','test*.py','-v')
```

35项测试与实际tokenizer检查各有作用，均不证明分类收益。额外子代理盲复核仅8/16，API有效JSON为质量46/48、争议7/16，不能把成功HTTP200等同语义通过。下一次GPU训练另须授权。
