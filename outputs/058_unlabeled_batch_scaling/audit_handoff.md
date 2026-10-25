# 058 独立审计交接

058已完成执行，独立审计未执行。

重点核查：
1. 方法完全复用057 run057.py；
2. 只改变batch size：240/480/960/1920/3840；
3. 两方向、六prior场景，共60条件；
4. 每条件1000次H0 calibration，H0/H1各500次；
5. n=960 mean detection：052=0.9943，053=0.9737；
6. n=960 minimum scenario detection：052=0.970，053=0.866；
7. n=1920两方向所有六场景均1.000；
8. H0 false-alarm约0.04–0.06；
9. n>236/237来自类内有放回重采样，不等价真实新增独立claim；
10. 0 API、reserved=false、未修改057、未commit/push。

主要文件：protocol.md、run058.py、freeze.json、scaling_summary.csv、aggregate.csv、run_summary.json、report.md、CURRENT_STATUS.md。
