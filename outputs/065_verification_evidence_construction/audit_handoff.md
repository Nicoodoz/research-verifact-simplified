# 065 独立审计交接

065已完成执行与executor verification；独立审计未执行。

重点核查：
1. cohort selection不读GT：8患者×(1 boundary + 2 stable)=24；
2. screen_cases_blind.jsonl不含GT；
3. planner只看claim；
4. B只允许C48候选；
5. C使用031 eligible corpus，claim dense/BM25 + planner query/requirement BM25后RRF top24 external；
6. B/C composer prompt相同，不输出最终三分类；
7. final DeepSeek只看claim+逐字raw-EHR reference；
8. 不使用U2/PriorG/Gate作为最终判定；
9. stage1=48、stage2=48、stage3=46 jobs；
10. 同一claim的B/C composer因max_tokens截断JSON，HTTP200不重跑，按Amendment 001记missing；
11. 142/142 HTTP200，费用约¥2.604783；
12. common-valid N=23；
13. A=14/23，B=15/23，C=15/23；
14. B vs A=3 rescue/2 harm，net+1，false-S +1；
15. C vs A=2/1，net+1，false-S +1；
16. C vs B=1/1，net0；
17. B/C均未过预注册门槛，C无incremental retrieval win；
18. B三个rescue均来自C48内聚焦；
19. C final Judge在7/23 common-valid病例引用了external证据，但未形成净分类收益；
20. verification_001.json 21项PASS。

主要文件：protocol.md、protocol_amendment_001.md、prepare065.py、common065.py、run065.py、build_stage2_065.py、build_stage3_065.py、analyze065.py、analysis.json、results.csv、report.md、CURRENT_STATUS.md、verification_001.json。
