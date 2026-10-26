# 066：Oracle Headroom Decomposition

066冻结现有后处理 T-S + Frozen PriorG，把053剩余39个错误拆成前处理与LLM推理headroom。

主要结果：
- baseline MCC 0.5607；
- same-reference observed reasoning oracle MCC 0.7101；
- GT-aware raw-EHR evidence oracle + 当前T-S+PriorG MCC 0.6680；
- 二者并集 MCC 0.7968。

错误四格：reasoning-only 11、evidence-only 8、both 3、neither 17。

Evidence Oracle修对11条中，9条关键passage本来已在C48但原final pack没完整选入，1条原final reference已有全部oracle证据但重组后才修复，仅1条需要C48外证据/混合检索。当前前处理首要瓶颈因此是C48→final reference，而非扩大retrieval。

该任务是GT-leaking oracle/headroom诊断，不是可部署方法或最终论文成绩。最终Judge从不接收GT，只看真实原始EHR reference。

113/113 HTTP200，费用约¥2.30，reserved未使用，143项executor verification PASS，独立审计未执行。
