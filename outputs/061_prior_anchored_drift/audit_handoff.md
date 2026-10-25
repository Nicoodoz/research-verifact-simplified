# 061 独立审计交接

061已完成执行；独立审计未执行。

重点核查：
1. formal HEAD=5ebf59940c7499f0eb94f3cbdb030fdca476ffc3；
2. 061不改变060的source mixture、tau、covariance shrinkage、clip与EM收敛规则，只固定prior；
3. Oracle-fixed使用真实target prior，仅作诊断；BBSE-fixed不读target GT；
4. BBSE Frozen monitor复现054真实prior估计；self-test逐方向核验到1e-6；
5. actual_unlabeled.csv只包含BBSE-fixed结果，先写入并记录SHA256=66a7c2eb1c95408e69ca2e4e14f8e9b1736b0858ca632c8b7ad53e7d3aa896c7，之后才生成Oracle/GT评价；
6. synthetic共2 source ×4 prior ×3 batch ×6 drift ×2 mode=288汇总行，每条件30次；
7. n=960 Oracle delta MAE=0.40679、sign=0.96778，事前Oracle门槛FAIL；
8. n=960 BBSE prior L1=0.09179、delta MAE=0.42841、sign=0.96042；
9. 真实052→053 BBSE/Oracle R2=0.30035/0.30723；
10. 真实053→052 BBSE/Oracle R2=0.06570/0.09709；
11. 两方向BBSE prior L1=0.02276/0.03119；
12. 060 free-prior R2=0.00406/-0.25360；固定prior有改善但不足；
13. synthetic none在Oracle-fixed下仍有约0.425 delta MAE，提示spurious drift；
14. 0 API、reserved=false、未commit/push；
15. 不根据061结果调整tau、mixture、starts或门槛。

主要文件：protocol.md、run061.py、freeze.json、actual_unlabeled.csv、synthetic_summary.csv、actual_evaluation.csv、run_summary.json、report.md、CURRENT_STATUS.md。
