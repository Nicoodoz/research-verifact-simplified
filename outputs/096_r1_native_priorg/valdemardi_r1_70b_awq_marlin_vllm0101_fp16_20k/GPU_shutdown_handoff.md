# R1_INFERENCE_DONE — 请关闭AutoDL

backend为AWQ-Marlin，Tier A；正式1143个HTTP200，core有效1142。校准/自然/诊断：{'calibration': 143, 'natural': 800, 'diagnostic': 200}。并发12，推理跨度103.18分钟，prompt/completion token 3616417/828036。跨度含benchmark之间的本地间隔，不等于实例完整账单。

全部原始响应已本地保存并对账。现在可以关闭AutoDL实例；按最新用户指示，等待其确认关闭后再离线拟合PriorG、读取GT评价、bootstrap及报告。当前没有完成科学评价，也未升级默认。GPU小时价/完整租金未知，未伪报为0；新增token API0元。

恢复命令见MARLIN_README.md。旧AWQ仅诊断，不进入任何正式列；旧P1两个unknown不补跑。本次不为表格/报告继续发送GPU请求。
