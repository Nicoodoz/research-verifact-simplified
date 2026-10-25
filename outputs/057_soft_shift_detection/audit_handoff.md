# 057 独立审计交接

057执行已完成；独立审计未执行。

重点核查：
1. formal HEAD=5ebf59940c7499f0eb94f3cbdb030fdca476ffc3；
2. protocol/code/input hashes见freeze.json，均已人工复核一致；
3. 052/053池分别236/237，来自055 full-Qwen features且T-S有效；
4. target实际alarm链路不读取target GT；actual_unlabeled.csv先写入并记录SHA256=350450a2aa5c053b47bf18bd89164746165872a8ec1635d2891ee5a836798e41；
5. prevalence sensor与056一致，使用DeepSeek Frozen PriorG hard predictions + source confusion做constrained BBSE；
6. soft主视图固定为DeepSeek T-S + Qwen共6维scores；
7. transform全部source-only：z-score、source pairwise distance median bandwidth、固定seed 128维RFF；
8. stress test共2 source × 6 prior × 4 batch=48条件；每条件1000 H0 calibration，H0/H1各500次；
9. H1保持prior不变，仅将P(scores|Y)替换为另一批真实类条件行为；
10. n=240 H1 detection：052 source 0.6443，053 source 0.5657，均未达0.70门槛；
11. n=480 detection升至0.8833/0.8187，仅说明大batch signal增强；
12. 真实052↔053 joint detector均未alarm，DS-only/Qwen-only也均未alarm；
13. 0 API、reserved=false、未commit/push；
14. 不按结果继续调RFF维度、bandwidth、transform或threshold。

主要文件：protocol.md、run057.py、freeze.json、actual_unlabeled.csv、actual_evaluation.csv、simulation_summary.csv、screen_summary.csv、run_summary.json、report.md、CURRENT_STATUS.md。
