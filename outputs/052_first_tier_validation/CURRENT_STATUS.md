# 052 当前状态

052已完成：24名development患者、每患者hash抽10条，共240条patient-balanced随机claim；四路DeepSeek N-S/N-V/T-S/T-V各240，固定12条四路repeat，fresh U2候选22条Qwen Gate peer。reserved overlap=0。

核心结果：
- 原VeriFact：195/240，MCC0.4949，false-S12；
- U2：190/240，MCC0.4464，false-S13；
- patient-out Gate A：187/240，MCC0.4504，false-S10；
- N-V：181/240，MCC0.4608，false-S6；
- T-S+U2：188/240 missing-as-error，236有效PA79.66%、MCC0.5435、false-S5；
- T-V：175/240 missing-as-error，MCC0.4806、false-S3。

T-S+U2 vs U2共同236条：21 rescue/20 harm，净+1，false-S -8，ΔMCC +0.0927，患者bootstrap95%区间[-0.0144,+0.1872]。
T-S+U2 vs patient-out Gate A共同236条：21/17，净+4，false-S -5，ΔMCC +0.0894 [0.0020,+0.1690]。

Operational sensitivity：4条T-S核心无效时退回同期U2，则191/240、MCC0.5399、false-S5；相对U2净+1且false-S -8；相对Gate A净+4且false-S -5。该fallback为post-hoc部署敏感性，不替换冻结主结果。

Human-written 135条是最强子组信号：T-S+U2正式101/135（132有效PA76.52%、MCC0.5928、false-S3），invalid→U2时103/135、MCC0.5877；U2为95/135、Gate A 94/135、原VeriFact99/135。Human fallback vs Gate A ΔMCC +0.1341，患者bootstrap95%区间[0.0041,+0.2426]。

051训练的G/M校准未迁移，T-S G/M等于raw并明显低于固定U2；N-V→T-S/T-V cascade在052产生净harm，停止；N-V/T-V的051 overall accuracy优势也未复现。

稳定性：12条repeat中N-S U2、N-V、T-S raw均12/12一致；T-S+U2 11/12；T-V 10/12。

API共1030次、1030/1030 HTTP200，usage估算¥19.369866/¥80 cap。Executor verification 7261项PASS；独立审计未执行。

执行顺序限制：GT-blind抽样/API/训练隔离均成立，但GT_connection在全部主预测完成前已物化，所以052定位为development内部探索性同场验证，不是严格解盲确认或新的reserved test。
