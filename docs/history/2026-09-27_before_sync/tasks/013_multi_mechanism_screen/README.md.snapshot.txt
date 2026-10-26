# 013_multi_mechanism_screen

**2026-09-15快速独立审计PASS，可冻结／结项。** 四分支均未通过固定231条压力筛选，停止扩大，没有组合/新患者确认。唯一必读：[中文主报告](../../outputs/013_multi_mechanism_screen/report.md)。原C48保留作对照，剩余16名development与40名reserved test不动。

完整约束、事前样本/门槛、预算和条件确认范围见[协议](../../outputs/013_multi_mechanism_screen/protocol_001.md)。任务共同baseline是009冻结C48的实际reference与本轮同期structured Judge；不复用旧009/010或unit Judge答案替代screen。

|实现|用途|
|---|---|
|`mechanisms013.py`|字面主谓合同、只补否定/条件前缀、两路top80并集、原C48候选ID选择；不接收GT/source|
|`prepare013.py`|冻结195错误并集＋36稳定正确、机制探针、原文锚点、费用估算|
|`native_stage013.py` / `io013.py`|复用011断点/原回执流程及008官方传输；单任务锁、全阶段累计40元上限；从account_2开始|
|`analyze_units013.py`|机制而非泛化评分；语义回查与机器门槛分开|
|`build_screen013.py`|所有晋级分支同期请求、完整body缓存、refresh48容量控制、12次baseline重复|
|`score013.py`|002评价、作者/类别/患者转移及事前门槛，机制复核后才形成最终gate|
|`diagnose_inputs013_final.py` / `measure_mechanisms013.py`|现行输入诊断002、逐字复述/实际输入量、原文到候选/重排/打包追踪；不作为医学金标|
|`prepare_review013.py` / `view_screen013.py`|预先登记的正反/稳定选例和完整输出、原始布局阅读；未显示不等于不在reference|
|`render_review013_final.py` / `case_corrections.json`|当前35例诊断review_final_002；修正初稿三处成员误读，旧文字/代码保留|
|`backcheck_membership013.py` / `verify013.py`|16项成员断言、174项断网测试、回执/评分/历史重放|

使用Conda `research-verifact`，新目录不得覆盖。带`native_stage013.py`的命令会真实计费；运行必须有013 authority、对应冻结请求和前置gate。执行者自查不是独立审计。

```powershell
E:/miniconda3/envs/research-verifact/python.exe -B -m unittest discover -s tests -p test_multi_mechanism_screen013.py -v
E:/miniconda3/envs/research-verifact/python.exe -B tasks/013_multi_mechanism_screen/verify013.py --output outputs/013_multi_mechanism_screen/verification_replay_002
```

`precharge_draft_001`是模型调用前的预算准备草稿；四分支全跑加确认不一定能在40元内完成，旧39.8是错误的无条件概括，已撤回。现行authority按第一阶段实际规模估算，后续每阶段根据实际淘汰及剩余任务额度检查；不以拆阶段增加总授权。样本、方法和门槛没有看到新方法结果后修改。

全部1435请求/1436尝试已结束，只有1次通信未知后原样重试成功；原未知预留保留。总费用估算/预留18.80024461元，不是账单。与002一致的六个条件各231条预测完整；停止不是预算耗尽，也不等于所有一般机制已被否定。

交审版本/指纹和历史草稿修正说明见[审计交接](../../outputs/013_multi_mechanism_screen/audit_handoff.md)。根README、AGENTS及审计索引可正常更新，不作为永久重放依赖；冻结计算代码、真实输入/回执、GT和结果继续严格检查。完成后不继续改同批成果，不自行宣告独立审计PASS。

当前独立结论见[013审计](../../reviews/013_multi_mechanism_screen.md)。原报告与交审快照保留其形成时状态，四分支停止、不做组合或新患者确认。

当前停止状态：001–013均已完成并有相应独立审计。下一步建议先整理已有对照、标签边界与失败证据，重新论证研究问题；不是继续执行本页列出的收费入口。新任务范围另行确定，最新状态以[根README](../../README.md)为准。
