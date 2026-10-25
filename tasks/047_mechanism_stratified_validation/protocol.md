# 047：Mechanism-Stratified Validation

## 目标

045/046提示至少两类错误并存：证据已在E0但Judge误解，以及证据选择/呈现可能改变Judge使用。047不继续扩方法数量，而是在development内部做患者隔离的筛选→确认。

本任务不使用reserved40。044训练样本的10名development患者按固定哈希分成5名screen、5名confirmation；两阶段患者不重叠。045/046使用的是044另一组evaluation患者，因此其成功病例不进入047主证据。

## 三个候选与同期基线

B：原E0 + DeepSeek-V4-Flash-0731，同期基线。
J：完全相同E0、相同structured/scoring prompt，仅将Judge改为Qwen3.8-27b；正式终点看Qwen原生verdict，不套DeepSeek λ=2。
P：不加入任何新证据。本地解析E0证据块，按claim-token overlap把最相关2块移到reference前部，其余保持原相对顺序，再由原DeepSeek判断。
S：Qwen只做evidence selector，从031原C48候选中未进入E0的原始EHR passage里选最多3段；程序截取与claim最相关的连续短原文窗，再追加到完整E0；最终仍由原DeepSeek判断。

任何Qwen选择理由、摘要或判断都不是患者证据；最终Judge只能看到原始EHR文本。GT不进入任何047 API请求。
## Screen

患者按 SHA256("047/patient/v1:"+sid) 排序，前5名为screen、后5名为confirmation。

Screen从前5名患者的044固定240条训练样本中选择24条：按044历史OOF base正确/错误各12条，先覆盖GT×author可用格，再固定hash补足；同患者最多6条。历史OOF只用于冻结诊断样本，047方法比较全部使用同期新B回答。

每条screen运行B、J、P、S-selector；S确实改变reference时才运行S-final。另固定6条B同输入repeat，只诊断运行波动。

候选晋级规则全部预先冻结：
- raw verdict相对同期B净正确 >= +2；
- rescue >= 2；
- rescue来自至少2名患者；
- harm <= 1；
- false-S不得增加。
最多保留2个候选。没有候选达到门槛则047停止，不执行confirmation。

筛选数字只用于路线选择，不报告成总体benchmark准确率。
## Confirmation

只有screen晋级后才创建confirmation。使用后5名患者，从044固定train_cases中按患者内固定hash轮转抽64条，不使用GT或历史正确性决定入选；方法、prompt、P规则、S selector/window均不再调整。

同期运行B及最多2个晋级候选。主终点为raw verdict的paired rescue/harm、净正确、PA、MCC、false-S、三类recall和患者方向。另报告作者分组、标签转移、reason引用合法性及API/token成本。

若S晋级，selector调用计入部署成本；未改变reference时与同轮B共享相同完整Judge body，不重复调用。J不使用DeepSeek λ=2；P/S可离线计算固定DeepSeek U2作为辅助，但不能替代raw verdict主终点。

## 完整性、预算和解释边界

Screen收费API累计保护上限8元；047全任务累计保护上限30元，远低于长期80元默认政策。HTTP200不因结果重跑；未知结果不自动重发。请求前落盘，回执append-only。

044存在源码provenance warning，因此047只读取其冻结train_cases、OOF/model结果等artifact，不调用当前044源码重建历史方法。

执行者自检与独立审计分开。047成功最多支持development内部、规则冻结后的患者隔离信号；reserved40已在036消费，不重新称为未见test，也不把自动reason检查当医生解释gold。

若超过2个候选同时晋级，固定排序为：净正确更多 → harm更少 → rescue患者更多 → 部署额外LLM调用更少；仍并列时按 P、J、S 顺序。该规则在047首次API调用前登记。
