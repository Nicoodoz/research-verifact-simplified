# 068 预检修订 002：067 的实际干预是替换/聚焦

在任何 068 API 请求发送前，对 067 冻结工件作逐 ID 核查：236 条 `cases_blind.jsonl` 的 `baseline_pids` 全为空；227 个正式 audit 请求的 `current_pack_ids` 全为空。226 个 changed pack 的最终 reference 只包含选择的 1–2 个 C48 passage，原 baseline reference 平均约 12 个 passage。`dropped_pids=[]` 只表示程序没有执行显式 drop，不能证明原段落被保留。正式 Judge 请求体与 `pack_mapping.jsonl` 的最终 reference 一致。

因此 067 的实际受控比较是“原包 vs 从 C48 重新选 1–2 段的聚焦/替换包”，其中可能包含原已见证据，也可能包含新证据；并非协议所述“原包全保留＋最多补2段”。源于 `prepare067.py` 接受空 `reference_blocks` 的映射，`build_stage2_067.py` 再以空 `baseline_pids` 构造新包。067 的原指标是这些真实请求的观测结果，但原机制解释失效。

`freeze.json` 和 `freeze_002.json` 在发现此问题前生成，均保留为预检快照；`jobs_002.jsonl` 的 78 个请求仍是精确复用原包/正式替换包的同输入重复，适用于问题 2。没有安全的“仅呈现原包”对照，因为 067 没有完整映射 baseline passage ID；不进行该对照，也不借机开发新 packer。发送前把重复请求清单作为 `freeze_003.json` 再确认。对问题 1 只做原始文本覆盖的离线归因和有限历史参照；不能宣称分离了删除干扰、新信息、组合、呈现的因果效应。

原 067 中 14 rescue、13 harm 全覆盖与 12 个按 ID 哈希选取的不变对照仍保留。任务总收费上限10元、冻结 Judge/Frozen PriorG、不用 reserved、不按答案重跑的规则不变。若重复执行未完成，须逐 ID 报告缺失且不作完整稳定性结论。
