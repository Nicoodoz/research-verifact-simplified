# 015：分歧证据仲裁

**2026-09-16修订定向独立复核PASS，R1/R2关闭，可冻结／结项。** 当前结论见[独立审计末尾](../../reviews/015_disagreement_adjudication.md)。原研究结果和停止边界不变；下文旧待审措辞保留形成时含义，不自动续跑。

用户交办验证014两模型互补能否转化为明显收益。先用014同650条、固定C48，仅在78条分歧上运行仲裁及一个无候选信息的同提示对照；一致572条不调用。原GT只用于评价，不进入请求。

任何收费调用前冻结[协议](../../outputs/015_disagreement_adjudication/protocol_001.md)、输入及全任务40元预算。**执行与自查完成，无winner，停止本方向**：仲裁523/650，V4 526、Qwen527、无候选重判542；相对最强单模型净−4，相对对照−19。没有新患者确认、不做v2/v3。独立审计未开展。

唯一必读[中文主报告](../../outputs/015_disagreement_adjudication/report.md)。全部156次请求有效，usage估算¥2.0524446（无失败/未知预留，非账单）；19例完整材料、50处引用；189项断网测试与60个内容文件重放通过，13,202个历史文件未变。技术入口为[审计交接](../../outputs/015_disagreement_adjudication/audit_handoff.md)。

Conda `research-verifact`环境离线复核（输出目录须不存在，不调用API）：

```powershell
python -B tasks/015_disagreement_adjudication/verify015.py --output outputs/015_disagreement_adjudication/verification_audit_001
```

`run015.py`是已停止的真实收费执行器，不因本目录存在而自动续跑。准备与执行代码/协议为调用前版本；分析、阅读解释和主报告在结果后生成。自查不替代独立审计，不改写001–014成果或原GT。

## 2026-09-16：审计阻塞执行修订

独立快速审计已核对停止结论；与014共用的R1/R2修订完成，待定向独立复核，见[015修订入口](../../outputs/015_disagreement_adjudication/revision_001/README.md)。保留旧验证器、原协议/清单/回执/报告；可变顶层入口仅作状态诊断，计算绑定仍严格，补齐Windows字节保护。每任务196项断网测试通过，015的60个内容文件重放不变。无API、无新患者、无winner，不提交推送。
