# 064 独立审计交接

064已完成主实验、Amendment 001、Amendment 002与executor verification；独立审计未执行。

重点核查：
1. formal HEAD=2f454b412405fac9ab0c23717feb3506268309a4；
2. policy library固定为BASE/V80/V60/R90/C80/C60；
3. target-GT-blind actual_unlabeled.csv在oracle前写入，SHA256见run_summary；
4. source signature prior总强度固定1.0，Jeffreys shape来源于source GT；
5. policy认证固定：mean Δcorrect>0、P(Δcorrect>0)>=0.80、rescue false-rescue mean<=25%、veto S-harm mean<=25%；
6. active_policy前三个标签覆盖三个disagreement signatures，之后按action-decision uncertainty；
7. oracle完整GT仅作诊断：052→053=R90，053→052=BASE；
8. 052→053 R90真实correct gain=+5，false-rescue=1/6；
9. 053→052 R90 gain=0，false-rescue=2/3；
10. main same-batch rows=802，summary=18；
11. Amendment 001 future评估因policy exposure使用remaining calibration counts产生语义错误，已superseded但文件保留；
12. Amendment 002只修正future exposure：使用完整calibration signature counts；其他方法与门槛不变；
13. v2 patient-disjoint rows=900，summary=18；
14. v2 forward active10：beneficial nonBASE select=0.58，unsafe=0，ΔPA≈+0.0106，ΔMCC≈+0.0127；
15. v2 reverse active20：BASE fallback=0.90，unsafe=0.10；
16. 没有budget达到两方向全部预注册闭链条件；
17. R90 region：052共3条/3患者，GT=1S/1NS/1NA；053共6条/6患者，GT=5S/1NA；
18. 29项verification PASS；
19. 0 API、reserved=false、未commit/push；
20. 不得把结果写成“10 labels足够”或“20 labels足够”；最接近的是forward active10但认证率仅58%。

主要文件：
- protocol.md
- protocol_amendment_001.md
- protocol_amendment_002.md
- run064.py
- run064_future.py（superseded评估）
- run064_future_v2.py（最终future评估）
- verify064.py
- outputs/.../report.md
- outputs/.../future_v2_report.md
- outputs/.../run_summary.json
- outputs/.../future_v2_run_summary.json
- outputs/.../verification_001.json
