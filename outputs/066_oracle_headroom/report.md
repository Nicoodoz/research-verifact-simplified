# 066：Oracle Headroom Decomposition

## 核心结论

固定当前最稳后处理 **T-S + Frozen PriorG**，把剩余误差拆成前处理与LLM推理两层后，053的240条development样本得到：

| 条件 | Correct | PA | MCC | false-S | S / NS / NA recall |
|---|---:|---:|---:|---:|---|
| 当前 T-S + PriorG | 201/240 | 83.75% | 0.5607 | 8 | 88.72 / 50.00 / 67.74% |
| Observed Reasoning Oracle | 215/240 | 89.58% | 0.7101 | 6 | 91.79 / 92.86 / 74.19% |
| GT-aware Evidence Oracle + T-S + PriorG | 212/240 | 88.33% | 0.6680 | 6 | 92.31 / 57.14 / 77.42% |
| Combined Oracle | 223/240 | 92.92% | 0.7968 | 4 | 94.36 / 100.00 / 80.65% |

这些都是development内部的oracle/headroom诊断，**不是可部署方法成绩**。

Observed Reasoning Oracle使用GT事后从同一reference的现有预测中选择正确者；Evidence Oracle允许GT进入planner/composer以挑选真实EHR证据，但最终DeepSeek Judge绝不看到GT；Combined Oracle取二者可修复错误的并集。

## 当前39个错误如何分解

T-S + PriorG共有39个错误：22 S、7 NS、10 NA。

| 错误类型 | 数量 |
|---|---:|
| 仅Reasoning Oracle能修 | 11 |
| 仅Evidence Oracle能修 | 8 |
| 两者都能修 | 3 |
| 两者都未修 | 17 |

所以：
- Reasoning Oracle共修 **14/39**；
- Evidence Oracle共修 **11/39**；
- 两者并集共修 **22/39**；
- 仅3条重叠，说明两层headroom高度互补，而不是在反复修同一批错误。

### 按GT类别

Reasoning-only：
- S 4
- NS 6
- NA 1

Evidence-only：
- S 5
- NS 1
- NA 2

Both：
- S 2
- NA 1

Neither：
- S 11
- NA 6

最明显的类别结论是：
1. **7个NS错误全部可由两个oracle之一修复**，其中6个是reasoning-only。NS主要是推理/语义边界问题。
2. S仍有明显的前处理与推理双重headroom。
3. NA最难。10个NA错误只有4个被并集修复，6个仍未解决，提示缺失语义、scope或GT/evidence可见范围问题。

## 前处理瓶颈定位

Evidence Oracle修对11个当前错误。

主归因：
- C48内 selection/composition：10
- retrieval or mixed：1

进一步逐条比较oracle所选原始passage与原最终reference：

| 前处理瓶颈 | 修复数 |
|---|---:|
| **关键passage在C48，但原final pack没完整选入** | **9** |
| passage原本已经全在final reference，仅重组/聚焦后修复 | 1 |
| 至少需要C48外证据 / mixed | 1 |

因此，本轮最强的前处理结论是：

> **剩余可观察前处理headroom几乎不在扩大检索范围，而在 C48 → final reference 的证据选择、packing与composition。**

也就是说，当前C48本身已经覆盖了绝大多数能由证据优化修复的case；主要损失发生在如何把C48变成Judge真正看到的证据包。

## LLM推理瓶颈

Observed Reasoning Oracle固定当前reference，只在已有同证据判断之间做GT-oracle选择：
- DeepSeek non-thinking raw；
- DeepSeek thinking raw；
- Qwen U0；
- Frozen PriorG。

它将MCC从0.5607提升到 **0.7101**，修14/39错误。

尤其：
- NS 7个错误中6个由reasoning-only修复；
- thinking实验051已经反复显示 plan vs completion、条件计划、确定性等语义边界会改变错误结构；
- 037显示NS/NA仍存在显著不可分/交换问题。

因此当前推理层的主要瓶颈不是“模型参数不够大”，而更像：
1. complete proposition support：是否支持整个claim，而非只抓相关事实；
2. plan / ordered / refused / completed事件状态；
3. temporal relation与scope；
4. possible / suspected / confirmed等确定性；
5. NS vs NA：被证据反驳/不完整 vs 根本没被涉及。

## 两层结合后的实测headroom

Observed Combined Oracle达到：
- 223/240；
- PA 92.92%；
- MCC **0.7968**；
- false-S 4；
- NS recall 100%；
- S recall 94.36%；
- NA recall 80.65%。

这与066前的估算“理想组合大约MCC 0.78–0.83”高度一致。

但0.7968不是理论数学上限：
- Evidence Oracle本身只是一次GT-aware Qwen证据选择，不保证真的达到医生级完美证据；
- Reasoning Oracle只在已有reasoner输出中选优，也不是完美reasoner；
- 因此更准确地说，**0.797是现有材料下已经实际观测到的经验oracle headroom点**。

## 剩余17条

17条两个oracle都没有修复：
- S 11
- NA 6
- NS 0

其中：
- 9条：GT-aware composer认为证据已经decisive，最终T-S+PriorG仍错；
- 4条：composer未构造出可用决定性pack，因此没有final Judge；
- 4条：composer认为证据仍不充分，但仍构造了pack，Judge仍错。

这提示剩余17条至少混有：
- 深层推理/label-contract问题；
- eligible EHR本身证据不足；
- NA/absence语义难题；
- claim强度、时间或GT scope与当前证据对象不完全一致。

不能把这17条全部归给任一单层。

## PriorG兼容性

在39个错误的新oracle evidence pack上：
- T-S raw直接修对10条；
- 加Frozen PriorG修对11条；
- 1条raw正确被PriorG改坏；
- 2条raw错误被PriorG救回。

所以当前证据没有显示PriorG在前处理改变后全面失效；它净多救1条。但以后前处理/推理正式变化后仍需重新做兼容性验证，不应继续优化PriorG本身。

## 研究优先级

### 前处理
主攻：
**C48 → final evidence pack**

重点研究：
- requirement coverage；
- decisive support / contradiction；
- time / negation / certainty / completion状态保护；
- 删除passage前验证是否会让某个material requirement失去覆盖；
- 保留保护证据，避免065式过度裁剪。

暂不优先：
- 单纯扩大top-K；
- 全EHR更大范围搜索；
- 更复杂generic reranker。

### LLM推理
其可观测headroom略大于前处理，而且对NS错误特别关键。

主攻：
-完整命题逐要求核验；
-事件状态与时间关系；
-支持强度/限定词；
-NS/NA边界；
-证据冲突综合，而不是简单“更敢判S”。

## 执行

- 39 GT-aware planner；
- 39 GT-aware evidence composer；
- 35 T-S thinking-high final Judge；
- 共113个API请求，113/113 HTTP200；
- usage费用约 ¥2.304612；
- reserved未使用；
- executor verification：143项PASS；
- independent audit未执行；
- 未commit/push。
