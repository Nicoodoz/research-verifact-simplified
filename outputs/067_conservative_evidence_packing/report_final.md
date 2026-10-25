# 067：Conservative Requirement-Preserving Evidence Packing

## 结论

067未晋级。

在052自然236条上，保持同一个T-S thinking-high Judge与同一个Frozen PriorG，仅把final pack替换为“原pack全保留 + 最多补2个C48 passage”的保守packing后：

| 方法 | Correct | PA | MCC | false-S | S Recall | NS Recall | NA Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline T-S+PriorG | 198/236 | 83.90% | 0.5946 | 6 | 89.30% | 38.89% | 77.42% |
| 067 Conservative Pack + T-S+PriorG | 199/236 | 84.32% | 0.5819 | 10 | 90.91% | 50.00% | 64.52% |

配对：
- 14 rescue
- 13 harm
- net +1
- 6 patient wins / 6 losses / 12 ties

预注册7项晋级标准仅2项满足，因此advance=false。

## 为什么失败

067本意是解决065的“过度裁剪”。因此强制：
- baseline pack默认全部保留；
- 只从C48补证据；
- 每条最多新增2段；
- 只有安全冗余baseline passage才允许删除。

实际结果：
- 227条有C48轨迹；
- 226条audit有效且最终都被修改；
- 共加424段；
- 0段被删除；
- changed pack平均多1.88段、约+1278字符。

因此方法从“过度裁剪”摆到了另一个极端：

> 几乎每条claim都追加上下文。

真正的瓶颈不是“C48里还有内容就补进去”，而是“什么时候存在一个足以改变核验质量的decision-critical gap”。

## Raw Judge告诉我们的东西

不套PriorG时：

| 指标 | Baseline raw T-S | 067 raw T-S |
|---|---:|---:|
| Correct | 177/236 | 177/236 |
| MCC | 0.5058 | 0.5159 |
| false-S | 3 | 3 |
| S Recall | 77.01% | 77.01% |
| NS Recall | 50.00% | 72.22% |
| NA Recall | 77.42% | 64.52% |

Raw层没有净正确收益，但MCC略升且NS recall大幅提高。

新增C48证据最明显的作用不是把更多case推成S，而是把NA区域向NS移动：
- GT=NS：平均NS score +19.17，NA score -19.39。
- GT=NA：平均NS score +10.38，NA score -11.07。

这解释了为何NS提升，同时NA显著受损。

所以新的前处理方法必须显式保护：

> “这个新passage是否真的address了claim的同一主体、事件、时间和关系？”

仅仅“主题相关”不够。

## PriorG兼容性

Baseline raw → Frozen PriorG：
- 23 rescue
- 2 harm

067 raw → 同一Frozen PriorG：
- 26 rescue
- 4 harm

新pack下PriorG多救3个true-S，但harm翻倍；new raw false-S仍为3，最终false-S变成10。

因此：
- packer本身没有增加raw false-S；
- 但前处理改变了score geometry；
- 固定PriorG在新分布上变得更激进。

这符合既定策略：后处理不是当前研究主线，但上游正式改变后必须做compatibility validation。

## 067对final pack问题的新定位

066证明：
- 9个oracle修复来自C48内遗漏；
- retrieval外扩只贡献1个修复。

067进一步证明：
- “普遍把C48漏掉的内容补回来”不行；
- 当前需要的是高精度、claim-specific的gap detection。

因此下一版final pack方法应该满足：

1. 默认NO-CHANGE，而不是默认augmentation。
2. 只有当当前pack存在明确material requirement gap时才允许补证据。
3. 新passage必须证明“新增了当前pack没有的decision-critical fact”，而不是仅相关。
4. 对NA特别要求exact addressability：同主体、同事件、同时间、同关系。
5. support与counterevidence必须成对考虑，避免direct_support成为默认addition。
6. 上游方法稳定后，再重新验证PriorG兼容性；不要同时调packer和后处理。

## Bootstrap

1000次patient-cluster bootstrap：
- ΔPA均值 +0.43pp，95%区间约[-3.80,+4.29]pp；
- ΔMCC均值 -0.0105，95%区间约[-0.101,+0.094]；
- Δfalse-S均值约+3.98，95%区间[0,+9]。

没有稳定总体收益信号。

## 执行与核验

正式请求：
- GT-blind Qwen audit 227
- changed-pack T-S Judge 226
- 453/453 HTTP200
- 正式费用约 ¥11.839566

正式预测完成后另出现一套superseded v2回执：
- 252 HTTP200
- 约¥8.894004
- 完全不同request_id
- 不参与正式结果

verification_002采用冻结artifact replay：
- 2984项PASS
- 0 FAIL
- 1 warning：common067.py冻结后追加辅助代码导致源码hash变化；实际stage2 builder hash、请求体、audit recommendation、pack mapping和final Judge reference均逐条验证通过。

reserved未使用；独立审计未执行；未commit/push。
