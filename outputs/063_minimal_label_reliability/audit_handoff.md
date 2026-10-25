# 063 独立审计交接

063已完成主实验、Protocol Amendment 001与executor verification；独立审计未执行。

重点核查：
1. formal HEAD=2f454b412405fac9ab0c23717feb3506268309a4；
2. 主protocol、amendment、两份代码及055/061输入hash均冻结并由verification通过；
3. budget固定0/5/10/20/40，非零budget每strategy每方向50 repeats；
4. 主评价从holdout中移除已标注claims，并与同一holdout Frozen PriorG比较；
5. 主063只用DeepSeek Frozen PriorG + Qwen U0两个真正不同Judge，9 joint patterns；
6. source pattern counts使用Jeffreys +0.5；
7. kappa只在few-label subset内部LOO选择；
8. active与active_soft选择逻辑均不读target GT；self-test用去GT数据确认索引一致；
9. oracle-balanced明确仅作诊断；
10. 主结果random/active/oracle-balanced均无passing budget；
11. 主oracle-balanced 40在052→053仍ΔNS=-0.500、Δfalse-S-rate=+0.186；
12. Amendment 001使用4维soft log-odds、source class means、pooled covariance+0.1I、BBSE prior；
13. Amendment仍无passing budget；
14. soft 052→053 active20/40虽ΔMCC=+0.071/+0.091，但NS recall分别下降0.571/0.500且false-S明显上升；
15. soft oracle-balanced40：052→053 ΔMCC=+0.080但ΔNS=-0.240；053→052 ΔMCC=-0.007且ΔNS=-0.216；
16. 因此不得写成“40 labels globally insufficient”；只能说测试的两类few-label calibrator到40均未闭合链路；
17. primary replicate rows=1202，summary rows=26；
18. soft replicate rows=1202，summary rows=26；
19. verification_001.json共24项PASS；
20. 0 API、reserved=false、未commit/push。

主要文件：
- tasks/063_minimal_label_reliability/protocol.md
- tasks/063_minimal_label_reliability/protocol_amendment_001.md
- run063.py / run063_soft.py / verify063.py
- outputs/.../replicate_results.csv / summary.csv / report.md
- outputs/.../soft_replicate_results.csv / soft_summary.csv / soft_report.md
- CURRENT_STATUS.md / verification_001.json
