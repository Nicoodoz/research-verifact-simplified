# 039 独立审计交接

独立审计待进行。重点复核：
1. 462 cohort与038 blind cohort逐ID一致，R/H/W=219/42/81。
2. query expansion请求只含claim；evidence audit不含GT/U2/RHW/reason。
3. 完整eligible corpus排序是否复用036原embedding并覆盖目标住院全部eligible passages。
4. C48 passage与新增32 passage是否去重。
5. A/B只能来自strict trace-supported；B必须引用C48外证据。
6. R A/B/C/D/U=66/55/94/1/3；H/W A+B=32/123。
7. 924个HTTP200没有因结果重跑；费用17.291343元。
8. 报告没有把自动审计当医生gold，也没有把D写成“完整EHR绝对无证据”。
