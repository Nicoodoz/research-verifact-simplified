# 017独立审计交接

状态：执行、分析及执行者自查完成；**尚未独立审计**。第一阶段gate=false，停止，未训练与未新患者确认属于预案的正常停止分支。

## 被审版本

- 基础HEAD：`87cb27de4ffe547b63594af3eba4682523cad74d`。017成果及现行导航目前为未提交修改；最终实际`git status`、所有017文件、代码、测试、导航指纹见`handoff_001.json`。
- 任务唯一主报告：[report.md](report.md)。原001–016冻结报告、代码、原生回执及独立意见保持。
- 事前方案与对象冻结：`protocol_001.md`、`preparation_001/manifest.json`（2026-09-16 08:58:34 UTC）。执行登记`authority_001.json`为09:05:22 UTC，在收费前；门槛代码被其绑定。
- `analysis_plan_001.json`于09:13:57 UTC绑定评分和单一模型实现，此时首批API已有返回，但尚未做GT效果评价。headroom门槛、样本和动作在收费前已冻结，未因结果调整；不声称所有实现代码均早于首份模型回执。
- 主报告初次渲染后补充了错误覆盖不足、类别不平衡及两轮波动的解释，未改门槛／评分／数据。当前报告可逐字节重新渲染，依据为`verification_report_001`；初版`report_source_manifest.json`只保留形成时信息。

## 重点审查

1. **GT盲性**：192条来自009/016完整1251条目录的患者×作者固定哈希前8条，不用013按错误选出的231条作为抽样框；干预脚本不读取GT／旧预测／理由。完整输入seal之后才导出评价GT，Judge仅见proposition/reference。
2. **最小干预**：三种动作仅交换一完整段，保留其余选择、段数、原formatter和prompt，90%–110%长度及每note≤2／总段≤16／8000字符控制。无合法动作保持baseline，并在同轮共享相同body。
3. **候选范围**：W为已有真实BGE打分的A48∪B48∪C48，47–77候选。没有刷新分数；不是013两路top80。013历史−5只能作范围不同的参照，不能当同队列因果对照。
4. **重复与归因**：两轮独立调用；稳定rescue/harm要求两baseline一致、两干预一致且供应商一致。保留全部单轮改对／改错及baseline翻转，不把两轮当384个独立病例、不挑答案。稳定rescue也只是固定Judge与医生verdict的一致性变化，并非医学evidence gold。
5. **完整效果与停止**：002完整192条分作者评价、1000次患者cluster bootstrap。稳定错误19<24，稳定rescue0、稳定harm3、训练配对2<16；不得补抽或训练挽救。不将headroom筛选失败写成已训练selector泛化失败。
6. **泛化隔离**：六训／六选事前确定但训练未触发；剩余10人只从002元数据表统计命题数量用于条件预算，没有读取其临床正文或利用GT开发；reserved test无逐例读取、分析或选择。
7. **执行与费用**：1574次尝试、1572有效回答；两次HTTP400 `code=20015 / JSON decode error`无答案，原body各重试一次成功。失败回执和0.119304元未知usage预留保留。累计13.37319060元／80元，未核账单，未重跑任何HTTP200。
8. **API与历史**：全程SF account_2；无全号池耗尽证据，未实测阿里云V4 fallback。路由预案不是同权重证明。新任务执行器含跨账号预算保护，旧001–016不改；`.gitignore`不改；不提交凭据。
9. **论证边界**：LLM侧只有3条稳定错误，S/NS/NA支持数91/4/1，不能从0/19推断全局无headroom。研究问题与FER／REPLUG／W-RAG／CUE-R有关，不声称utility或counterfactual选择本身首创。

## 离线复核

使用`environment.yml`对应的`research-verifact`环境，在仓库根目录执行（输出须全新）：

```powershell
python -B tasks/017_verification_supervised_evidence_utility/verify017.py --output outputs/017_verification_supervised_evidence_utility/verification_AUDITOR_FRESH
python -B tasks/017_verification_supervised_evidence_utility/report017.py --output outputs/017_verification_supervised_evidence_utility/report_AUDITOR_FRESH/report.md
python -B -m unittest discover -s tests -p test_utility017.py
python -B -m unittest discover -s tests -p test_evaluation.py
```

`verification_001`已核对1572个请求重建、1920个逻辑条件、32份分析文件逐字节一致、16403个历史文件保持（当时只有.gitattributes为允许的导航变更）；后续导航同步单独核对，不回写第一次验证快照。最终测试日志、环境版本与凭据扫描在`self_check_001`。这些都是执行者自查，不替代独立审计。

审计期间冻结本批成果；独立意见应另存于reviews，不由执行者填PASS。
