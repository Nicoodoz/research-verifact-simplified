# 066 独立审计交接

066用于development内部Oracle Headroom诊断，非可部署方法。

重点核查：
1. formal HEAD = 2f454b412405fac9ab0c23717feb3506268309a4。
2. baseline为053冻结 T-S+PriorG：201/240，MCC 0.5606605667。
3. 基准错误39：S22/NS7/NA10。
4. Evidence Oracle中GT允许进入planner/composer，只用于寻找/选择真实EHR passage。
5. final T-S Judge请求绝不能包含GT、oracle goal、requirements或composer rationale；只允许 proposition/reference。
6. final Judge必须复用053 T-S：enable_thinking=true, reasoning_effort=high, max_tokens=8192。
7. 39条错误全部绑定冻结eligible-EHR corpus；36/39可重建历史C48。
8. source counts：031=15,020=12,016=6,009=6。
9. Evidence Oracle final Judge jobs=35；4条composer未构造可用pack，不重试。
10. API 113次、113 HTTP200，cost≈2.304612 <20 cap。
11. Reasoning Oracle是GT事后选择已有same-reference prediction：NS_U0、TS_raw、Qwen_U0、PriorG；不可当部署router。
12. Reasoning Oracle：215/240，PA .8958333，MCC .7100934，false-S6。
13. Evidence Oracle：212/240，PA .8833333，MCC .6679633，false-S6。
14. Combined Oracle：223/240，PA .9291667，MCC .79677072，false-S4。
15. 39错partition：reasoning-only11 / evidence-only8 / both3 / neither17。
16. reasoning fixes14；evidence fixes11；union fixes22。
17. evidence fixes by GT：S7/NS1/NA3。
18. reasoning fixes by GT：S6/NS6/NA2。
19. Evidence主归因：C48_selection_composition10 / retrieval_or_mixed1。
20. 更细定位：C48→final pack omission 9；already-in-final-reference recomposition 1；retrieval/mixed 1。
21. 7个NS错误全被oracle之一覆盖，其中6 reasoning-only。
22. neither17 = S11/NA6。
23. neither17中9条composer标记decisive且final Judge仍错；其余8条为nondecisive/no usable pack等。
24. 新oracle evidence上raw T-S fix10、PriorG fix11；raw-only1、PriorG-only2。
25. reserved=false；未commit/push。
26. verification_001.json应为143项PASS，independent_audit=false。

主要文件：
- protocol.md
- protocol_amendment_001.md
- freeze.json
- error_cases.jsonl
- search_contexts.jsonl
- final_mapping.jsonl
- evidence_cases.csv
- analysis.json
- diagnostics_001.json
- report.md
- verification_001.json
