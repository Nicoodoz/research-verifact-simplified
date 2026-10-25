# 043：原Judge定向补证据效用验证

## 核心结论

043补上了039→042之间缺失的关键机制验证：**039定位出的新增证据，对原DeepSeek scoring Judge本身确实有明显效用。**

在55条post-hoc R-B样本中，原C48条件下DeepSeek只有7/55直接给Supported；加入039实际引用的关键EHR证据后，54条有效输出中20条直接给Supported。严格配对的54条里：

- B相对A：**13条 non-S→S，0条 S→non-S，净+13**；
- 患者层：9名患者正向、0名负向、19名持平；
- 描述性精确二项检验 p=0.000244。

与“加入等量但未被039引用的matched context”相比：

- B相对C：**14条 non-S→S，3条 S→non-S，净+11**；
- 患者层：11名正向、2名负向、15名持平；
- 描述性 p=0.0127。

因此，效果不能简单解释为“上下文变长了模型就更愿意给S”。**被039定位的目标证据具有特异的下游Judge utility。**

但这55条本身就是reserved后的GT=S/R/B条件样本，所以这是机制证据，不是新的无偏系统准确率。
## 1. 实验设计

固定55条样本均满足：

1. 036中U0为non-S、U2改为Supported；
2. 医生GT=Supported，因此属于R；
3. 039中原C48未通过Qwen strict trace，但加入外部EHR后通过严格Supported审计，即B类。

三个条件都使用完全相同的原DeepSeek scoring Judge：

- **A：原C48**；
- **B：原C48 + 039中Qwen实际引用的外部EHR passage**；
- **C：原C48 + 同数量matched control passage**。

B绝不删除原C48，只在末尾追加证据。55条共追加78个目标passage，平均新增约896.7字符。

C同样逐条追加相同数量passage，优先匹配note category与长度，但排除039引用passage、原C48 passage和精确重复正文；平均新增约932.0字符。

因此B和C的主要差别不是“有没有更多字”，而是**新增内容是否为039定位的目标证据**。

DeepSeek输入中没有GT、U2、039类别或旧reason。
## 2. 原Judge的标签变化

| 条件 | 有效N | Score verdict=S | U0=S | U2=S |
|---|---:|---:|---:|---:|
| A 原C48 | 55 | 7 (12.73%) | 7 | 44 |
| B 定向补证据 | 54 | **20 (37.04%)** | **20** | **51** |
| C matched context | 55 | 9 (16.36%) | 9 | 42 |

B有1条HTTP200缺少label_scores，按规则保留invalid、不重跑，因此涉及B的严格配对分母为54。

在54条B/A共同有效样本中，DeepSeek普通verdict和U0均为：

> **13 rescue / 0 harm / 净+13。**

B/C共同有效54条中：

> **14 rescue / 3 harm / 净+11。**

固定λ=2后的U2也朝相同方向：

- B vs A：9 rescue、1 harm，净+8；
- B vs C：12 rescue、2 harm，净+10。

不过U2不是本任务最稳的机制指标，原因见后面的重复实验。
## 3. 分数本身也明显移动

在B/A共同有效的54条中：

- A的Supported score均值：27.41；
- B：48.06；
- 平均增加 **+20.65分**；
- 27条升高、6条降低、21条不变。

B相对C的Supported score平均增加 **+18.70分**。

所以这不是只在几个恰好跨阈值的案例上发生标签抖动。定向证据在整体上明显推动了Judge的Supported评分。

同时，B并非让所有样本都自动变成S：54条有效B中仍有34条原Judge不直接给Supported。这说明“目标证据有效”与“目标证据足以让Judge完全接受claim”仍是两回事。

## 4. reason是否真的跟着标签走

DeepSeek round-0冻结后，另用Qwen做GT盲reason审计。Qwen只看到claim、该条件reference和DeepSeek自己的verdict/reason/checks，不知道A/B/C名称、GT或U2。

| 条件 | 审计有效 | reason consistent且grounded | DeepSeek=S中的consistent+grounded | 新增证据被判material |
|---|---:|---:|---:|---:|
| A | 55 | 51/55 (92.73%) | 6/7 | 不适用 |
| B | 53 | 48/53 (90.57%) | **18/19** | **26/53** |
| C | 54 | 50/54 (92.59%) | 8/9 | 4/54 |

所以不能说B让“所有reason总体质量”更高；三组本来就都较高。
更关键的是那13条A→B真正被原Judge救回的案例：

- 12条有有效Qwen reason审计；
- **12/12都被判为label-reason consistent且grounded**；
- 其中 **8/12** 被判定新增目标证据对reason有material贡献；
- 另1条reason审计结构无效，不当作失败。

这说明至少在一批案例中，补证据不是“标签变S但理由还停留在旧NS逻辑”，而是DeepSeek自己形成了新的、与S一致且有证据落点的解释。

典型例子包括：

- “最终脱离呼吸机”：A只看到weaning尝试和早期无法脱机，因此NS；B加入后续状态后，DeepSeek改为S，并说明已成功脱离ventilator、耐受trach collar。
- “最终转到普通病房”：A只看到transfer计划和延迟；B补入实际转入CC6/transfer记录后，DeepSeek改为S。
- “入院肌酐1.8”：A其实已经承认1.8，但因为后续1.6而过度严格地拒绝；补入额外一致记录后转S。这类案例说明B的作用不全是“找回完全缺失的事实”，也包括**增强已有但被Judge低估的证据强度**。

因此043把039的B类进一步拆出了一个重要事实：新增证据既可能补充缺失事件，也可能改变Judge对已有证据的权衡。
## 5. matched context为什么重要

如果只是“多给约900字符”就能使模型更容易给Supported，那么C应该接近B。

实际C只有9/55直接S，而B有20/54；B相对C净+11。

Qwen reason audit也显示：

- B新增内容被判material：26/53；
- C新增内容被判material：4/54。

因此目标passage的作用明显高于等量普通额外上下文。这给“检索到什么内容”而不是单纯“上下文长度”提供了直接机制证据。

不过C是自动构造的matched control，虽然排除了039引用证据并匹配类别/长度，但不能保证每条C在医学语义上绝对无关，因此它不是完美安慰剂。

## 6. 重复稳定性

事前固定hash选择12条，A/B/C分别独立重复一次。

score verdict的同条件标签变化：

- A：0/12；
- B：2/11共同有效；
- C：1/12。

固定repeat子集中，round 0的直接S数为A 0/12、B 4/11、C 1/12；round 1为A 0/12、B 6/12、C 0/12。

因此B效应方向在重复轮仍然存在，不像完全由普通随机翻转造成；但B并非完全确定性，仍有一定run-to-run变化。
U2重复稳定性反而更值得警惕：

- A：3/12变化；
- B：0/11变化；
- C：2/12变化。

注意：这55条按036定义原本全部是U2=Supported，但本次同期A重跑只有44/55为U2=S。这说明label_scores在当前服务调用之间有足以跨λ边界的波动。

因此043最可信的机制终点是**DeepSeek自己的普通verdict变化**，而不是把本次重跑U2数量直接与036历史U2数量混合解释。

## 7. 对042的重新解释

042的负结果现在有了更清楚的含义。

042并没有证明“补回证据没用”；043反而证明**某些目标证据补回后确实能使原Judge自我修正**。

042失败的是另一件事：

> SoftNote和CovMMR这两个通用本地规则，并不知道哪一段候选证据具有真正的downstream utility。

也就是说，当前瓶颈已经从：

> “有没有可用证据？”

进一步收缩成：

> **“怎样在不知道GT、也没有039事后oracle的情况下，从候选证据里识别那些真正会帮助核验的高utility passage？”**

这比继续无方向地增加候选数或多样性明确得多。
## 8. 现在能声称什么

043支持的结论：

> 在这批post-hoc选出的检索/证据缺口案例中，039定位的目标证据对原DeepSeek Judge具有实际下游效用；补入后，Judge更经常自行给出Supported，并能在多数新S输出中产生与标签一致、由reference支撑的reason。

043不支持的结论：

- 不能说整体系统准确率因此已经提高13/55；
- 不能把55条当成新测试集；
- 不能说Qwen找出的每条证据都足够；
- 不能直接把039 oracle evidence作为部署模块；
- 不能说已经找到可泛化的自动selector。

下一研究问题应该从“generic packing”转向**evidence utility prediction / targeted recovery**，而具体选择规则必须回到development开发，不能拿这55条reserved案例训练或调权重。

## 9. 执行、异常与费用

- DeepSeek scoring：201次调用（55×3 round0 + 12×3 repeat）；
- Qwen reason audit：164次调用；
- 总尝试365，365个HTTP200；
- DeepSeek：200 valid，1条B响应缺label_scores，保留invalid且不重跑；
- Qwen audit：162 valid，2 invalid，不重跑；
- usage估算总费用：**¥4.832436 / ¥35**；
- 执行者核验PASS；
- **独立审计未执行**。

主要机器结果：analysis_001/key_results.json、paired_effects.csv、reason_summary.csv、repeat_stability.csv、rescue_cases.csv，以及verification_001.json。
