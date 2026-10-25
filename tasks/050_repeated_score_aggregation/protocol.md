# 050：Repeated Scoring Aggregation

## 研究问题

043、047、048、049反复观察到：完全相同或近同输入下，DeepSeek raw verdict通常稳定，但scoring label_scores在固定λ=2边界附近足以使U2跨运行翻转。050不再修改retrieval、reference、prompt或Judge定义，只研究：

完全相同scoring prompt重复若干次后，预先固定的稳健聚合能否降低U2随机漂移，并在不增加false-S的情况下提高或保持分类表现？

这不是“多问几遍选最好答案”。所有HTTP200原样保留，不按GT、标签或score挑选某一轮。

## 数据与患者隔离

沿用048的8名development evaluation患者固定分区：
- 048 screen的4名患者作为050 screen患者；
- 048 confirmation的4名患者作为050 confirmation患者；
- 两组完全不重叠，reserved40不参与。

050 screen固定32条：
1. 048既有16条历史raw-vs-U2冲突病例；
2. 同4名患者再选16条稳定control，只依据044历史模型输出，不看GT：优先覆盖 raw=U2=Supported / Not Supported / Not Addressed 三类后固定hash补足，每患者4条control。

confirmation预先冻结：
1. 048已冻结的29条历史冲突病例；
2. 同4名confirmation患者再固定29条稳定control，同样只依据历史模型输出和固定hash，不看GT。

## Screen调用与两个独立三连组

每条screen病例使用完全相同的DeepSeek-V4-Flash-0731 scoring body调用6次，temperature=0、thinking=false、reference和prompt字节一致。六轮固定分成：
- Triplet A：round 0/1/2；
- Triplet B：round 3/4/5。

两个triplet分别独立产生聚合预测。不得把6轮合在一起后再根据GT选择规则；两个triplet的一致性是方法稳定性诊断。

每一轮保存raw verdict、三类label_scores、U0与固定U2。单轮基线报告6轮各自表现、平均正确数/false-S和逐病例U2标签变化；raw只作稳定性参照。

## 预先固定的3-run聚合规则

对每个triplet只使用其中3次label_scores：
1. Mean3：三次各类别score算术平均，再应用固定λ=2。
2. Median3：三次各类别score逐类中位数，再应用固定λ=2。
3. LogMean3：先对每轮各类score/100取log floor，再逐类平均，Supported类加固定2后argmax。
4. Vote3：三次各自U2多数票；若三类各1票，用Mean3打破平局。
5. Cons2：先取三次raw verdict多数票；若raw多数不是Supported，只有至少2/3次U2=Supported才覆盖成Supported，否则保留raw多数。
6. Cons3：同上，但只有3/3次U2=Supported才覆盖成Supported。

raw多数票本身单独报告，但不作为主要新方法。

## Screen晋级规则

每个聚合规则在Triplet A和B分别评价。单次调用参考不是挑最好一轮，而是6个single-run的平均正确数与平均false-S。

accuracy通道需同时满足：
- 两个triplet的平均正确数至少比6轮single-run平均正确数高1.5条；
- A、B两个triplet都不比各自首轮少超过1条正确；
- 两个triplet的false-S都不高于6轮single-run平均false-S向上取整；
- A/B聚合标签一致率至少90%。

risk通道需同时满足：
- 两个triplet平均false-S至少比single-run平均少1.5条；
- 两个triplet平均正确数不比single-run平均低超过0.5条；
- A/B聚合标签一致率至少90%。

最多保留2个规则；优先顺序为：两triplet平均正确数更高→平均false-S更低→A/B一致率更高→部署规则更简单（Vote3、Mean3、Median3、LogMean3、Cons2、Cons3）。这些门槛只决定是否值得进入下一批，不是显著性或临床安全证明。

## Confirmation

只有screen有规则晋级才执行预先冻结的58条confirmation。每条同样运行6次完全相同scoring请求，按冻结规则分别计算两个triplet；不得在confirmation重新选择规则或λ。

确认主结果：聚合规则相对6轮single-run平均、round0、raw多数的正确数、false-S、三类recall、患者方向，以及两个triplet的标签一致率。另报告冲突富集子集与control子集，但不把58条写成自然总体PA/MCC。

## 预算与完整性

050只调用DeepSeek-V4-Flash-0731，不增加Qwen/BGE。screen保护上限20元，050全任务保护上限50元；便宜时段不是花满预算的理由。

HTTP200不按答案重跑；未知结果不自动重发。所有重复body必须逐字一致（除request_id外），verification核对body hash。GT不进入任何API请求。任务结束不自动commit/push，不修改.gitignore。
