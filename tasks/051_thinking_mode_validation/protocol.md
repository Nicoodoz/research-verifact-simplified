# 051：Thinking Mode and Scoring Interface Validation

## 研究问题

固定原C48/E0、同一DeepSeek-V4-Flash-0731和同一三分类定义，拆开两个因素：是否开启thinking、是否要求label_scores。目标不是继续调retrieval或lambda，而是回答：一次更充分的模型推理，能否直接产生更正确、证据一致的最终verdict/reason，并减少对不稳定score后处理的依赖。

当前项目历史调用都显式 `enable_thinking=false`；051首次正式测试该快照的thinking模式。阿里云当前文档确认0731支持 `enable_thinking=true` 与 `reasoning_effort=low/high/max`；051固定high，不搜索强度。

## 四条件

- N-S：non-thinking + scoring，沿019 scoring prompt；正式最终输出为固定U2，raw/U0辅助。
- N-V：non-thinking + ordinary structured verdict/reason/checks，不要求scores。
- T-S：thinking high + scoring，同N-S prompt/schema；正式主要看raw verdict，T-U2只辅助。
- T-V：thinking high + ordinary structured verdict/reason/checks；主候选，最终标签和解释来自同一次回答。

thinking条件固定 `enable_thinking=true`, `reasoning_effort=high`, `max_tokens=8192`, temperature=0, stream=false。non-thinking固定原配置 `enable_thinking=false`, max_tokens=2048。不得在结果后改成max/low或换prompt。

## 患者与样本

排除048-050反复使用的8名患者后，031剩余development材料中固定16名患者作为051池。患者按 SHA256("051/patient/v1:"+sid) 排序，前8名screen、后8名confirmation，患者完全不重叠。

Screen固定48条，GT分层S/NS/NA各16；Confirmation在任何051结果出现前固定96条，各类32。抽样只在患者分组冻结后按固定hash进行；GT仅用于预先声明的类别均衡诊断抽样，不进入API或方法特征。两批都至少覆盖各自8名患者。

另固定1条development claim作为接口preflight，并从正式screen/confirmation排除。Preflight仅检查四条件实际可调用、thinking响应含reasoning_content/usage且最终content可解析；不用于科学结果。

## 主比较

Screen主比较按最终部署输出：
1. T-V vs N-S+U2：thinking直接判定能否超过当前后处理系统；
2. T-V vs N-V：thinking对ordinary Judge的增量；
3. T-S raw vs N-S raw：thinking对同scoring接口原生verdict的增量；
4. T-V vs T-S raw：要求label_scores是否影响thinking Judge的最终判断。

T-S U2、N-S raw/U0及概率质量仅作辅助；不能看完结果后把T-S raw/U2中较好的一个改成主方法。

## Screen晋级与稳定性

主候选T-V有两条事前通道：
- accuracy通道：相对同期N-S+U2净正确至少+3，rescue来自至少3名患者，false-S不增加，且S/NS/NA任一类正确数最多下降2条；同时T-V相对N-V净正确至少+2，才能把主要增量归因为thinking而非仅取消scores。
- risk通道：相对N-S+U2 false-S至少减少2，净正确损失最多1，风险改善涉及至少2名患者；同时相对N-V不能更差超过1条正确。

T-S raw作为辅助候选，仅当相对N-S raw净正确至少+3、至少3患者改善、false-S不增加，且相对T-V不优于1条以上时才允许进入confirmation；其固定lambda2版本永不作为051事后主方法。

固定6条screen病例对四条件各额外repeat一次，样本在正式结果前按hash确定。repeat不覆盖第一次回答。若thinking主候选通过性能门槛但T-V同输入repeat标签一致低于5/6，则不直接晋级，允许一次固定小批追加稳定性screen；否则按性能门槛决定。

## 语义最小对照

预先写12组、每组2条的合成短reference/claim，共24个逻辑测试项，仅比较N-V与T-V：时间先后、计划vs完成、拒绝vs完成、possible vs confirmed、当时考虑vs后来排除、局部稳定vs全程稳定、单次检查vs一系列、药物尝试vs持续治疗、程序成功vs无并发症、否定范围、条件句、状态变化。

这些测试有程序预定标签，仅作行为诊断，不混入临床PA/MCC，也不声称是新增医生gold。T-V若总体临床成绩提高但语义对照比N-V少对3组以上，必须在结论中视为反向证据，不能只报总体准确率。

## Confirmation与预算

只有screen晋级才执行已冻结96条confirmation；四条件全部重跑，规则和reasoning_effort不变。Screen含preflight、48×4主调用、6×4repeat、24×2语义测试，最多268次请求；screen保护上限20元，051全任务保护上限50元。费用用当前北京忙时3/9元每百万token作保守上界，实际usage单独记录；thinking chain与最终回答都计输出token。HTTP200不按结果重跑，未知结果不自动补发。

## Budget amendment before scientific screen

After preflight and after all scientific jobs were frozen, the conservative busy-hour/full-max-token reservation was 22.14 CNY, above the original 20 CNY screen reservation line but below the unchanged 50 CNY task cap. Before any scientific screen call, screen cap is amended to 25 CNY only. No sample, model, prompt, reasoning setting, output definition, comparison or stop rule changes.
