# 016 第一阶段冻结协议（取代未执行的 protocol_001）

## 科研问题与范围

015 evidence_only 是旧开发集上事后值得关注的对照，不是已验证方法。本任务只验证该信号在下一批新患者能否复现，并用同分歧集的普通重复排除“再问一次即足够”的解释。不修改检索、原 claim、医生 GT、C48、structured 定义或015 review prompt。

用户最新指示将本次全部收费调用硬上限设为40元，禁止预支后续阶段。protocol_001、preparation_001 和 precharge_history_001 保留为无收费旧预案，不再执行。

## 队列与输入

003冻结开发顺序第25–30名：87982、16076、55106、97683、4954、55750，全部601条valid atomic claims（LLM 189，human 412）。剩余10名及reserved test不进入本任务。只读取本队列原claim和原EHR，按009原代码生成一次C48；所有Judge共享相同reference。Judge仅见proposition/reference，无GT、作者、source/BHC、患者隐藏信息或候选答案。

## 单一实验

1. 全量同期V4 structured与Qwen structured，temperature=0、max_tokens=2048、enable_thinking=false，其余沿009/014。
2. 仅当两者合法标签不同，各运行一次V4 structured repeat与一次015原版evidence_only V4。普通repeat body与第一次V4完全一致，但作为预设独立调用，不从缓存返回。review body逐字复用015生成函数。
3. 同标签直接采用共同标签；分歧分别采用review或repeat标签，构成cross_review和cross_repeat两个完整流程。
4. 角色内相同完整body事前去重；保存逻辑样本映射。两个基础角色随机散列交错发送，分歧阶段两个角色也交错发送。不是严格随机抽样，也不能保证服务权重不变。
5. 只离线取得原VeriFact R1-70B发布系统同队列预测。它是整个历史系统参照，不是同C48或同期模型因果对照。

HTTP200回答即canonical，不因截断、格式或标签错误重生成。无答案网络错误有限重试并累计未知费用预留；402保留回执并按account_2、_3…顺序换号。缺失或非法标签不补GT、不做available-case主分析，完成性不满足则不能通过门槛。

## 预先固定的继续门槛（全部满足）

- 601条完整；cross_review总正确数比V4/Qwen中较高者至少多13条（ceil(2%×601)）。
- LLM/human分别比各自最强单模型至少多2/5条，MCC分别提高至少0.025，AC1均不低。
- cross_review比cross_repeat总净增至少7条；两个作者各自净增>0，MCC分别提高至少0.01。
- 对每个作者、每类别，相比V4正确数损失不超过max(1,floor(5%×该GT类别数))；false-S不超过两单模型中较少者+1。
- 至少4/6患者较V4净增；任一患者净损失不超过max(2,ceil(2%×该患者命题数))。

002统一valid-only三类评价；作者分开，1000次患者cluster bootstrap，固定完整队列、missing=error、原标签映射与paired_compare。总正确数为辅助总体概览，不代替作者分层。报告PA/AC1/MCC、类别PRF、混淆矩阵、患者变化、改对改错、分歧中V4独对/Qwen独对/都错的选择结果。分歧错误富集仅作描述，不当作门控因果效果证明。不能把模型理由当作内部机制证明。

## 费用及停止

使用硅基流动官网实时价格（保存价格核验记录），预发送估算以实际请求文本和同模型历史服务器usage的token/字符校准为基础，明确不等于服务器精确token计数；生成token采用历史高分位加余量。C48生成前先按8000字符上限和实际claim估算，生成后及已知分歧数后重新按完整body估算。实际结算由回执usage和公开价格计算，非账单核验。跨阶段、账号、重试与未知请求统一累加；每次发送先预留保守字节与最大输出费用，累计不得超过40。预计全任务超过40则停止并报告，不自动缩小样本或继续调用。

不执行全量repeat/review、hash/random触发、trigger改进、多prompt、剩余开发确认。任何条件失败即结束016；全部通过也仅报告“值得继续第二阶段”，无下一阶段自动入口。没有冻结后的最终确认，不能称论文方法已验证。
