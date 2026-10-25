# 067 独立审计交接

067正式结论：不晋级。

重点核查：
1. formal HEAD=2f454b412405fac9ab0c23717feb3506268309a4。
2. 052 T-S有效236条、24患者；baseline 198/236，MCC .5946094254，false-S6。
3. 227条可映射历史C48，9条unmapped保持baseline。
4. stage1正式227个GT-blind Qwen audit；payload顶层只含 proposition/current_pack_ids/C48_candidates。
5. 1条audit HTTP200但JSON无效，按冻结规则原pack回退，不重跑。
6. stage2正式226个changed-pack T-S Judge；最终payload只含 proposition/reference。
7. DeepSeek固定thinking-high scoring：enable_thinking=true, reasoning_effort=high, max_tokens=8192。
8. 226个pack changed；424 additions；0 drops；均值约1.876 additions。
9. 新正式结果199/236，PA .8432203390，MCC .5819131470，false-S10。
10. S/NS/NA recall 90.91/50.00/64.52%，baseline 89.30/38.89/77.42%。
11. paired rescue/harm/net=14/13/+1；patient wins/losses/ties=6/6/12。
12. raw T-S correct 177→177；MCC .5058498→.5159013；false-S3→3；NS 50→72.22%；NA 77.42→64.52%。
13. baseline raw→PriorG 23 rescue/2 harm；new raw→PriorG 26 rescue/4 harm。
14. GT=NS mean score delta: NS +19.17, NA -19.39；GT=NA: NS +10.38, NA -11.07。
15. preregistered advance=false。
16. formal API scope=stage1_jobs + stage2_jobs =453 HTTP200；formal cost≈¥11.839566。
17. post-formal stage1v2/stage2v2共252 HTTP200、≈¥8.894004，发生于正式stage2结束后，request_id不同，必须排除正式结果。
18. verification_001被false-positive checks supersede。
19. verification_002：2984 PASS、0 FAIL；warning为common067.py freeze后追加辅助代码hash变化。
20. stage2 builder代码hash与stage2_freeze一致；audit recommendation→pack additions→final Judge reference逐条artifact replay通过。
21. reserved=false；未commit/push；independent audit=false。

主文件：
- protocol.md
- protocol_amendment_001.md
- freeze.json
- cases_blind.jsonl
- stage1_jobs.jsonl
- pack_mapping.jsonl
- stage2_jobs.jsonl
- analysis_final.json
- diagnostics_final.json
- report_final.md
- verification_002.json
