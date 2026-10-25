# 065 当前状态

065已完成三臂verification-oriented evidence construction screen，并完成executor-side verification：21项PASS。独立审计未执行。

## 三臂

- A Baseline：当前E0/reference → 同一DeepSeek raw verdict。
- B Focus-only：不出C48，只让Qwen按verification requirements从同一C48中选最小充分原文证据，再交同一DeepSeek。
- C Retrieve+Focus：claim-only planner → eligible EHR requirement-aware检索 → 同一composer → 同一DeepSeek。

不使用U2、PriorG、Gate或任何post-hoc correction。

## 队列与完整性

GT-blind selection：
- 8名development患者；
- 每患者1条raw-vs-U2 boundary + 2条raw=U2且高置信stable；
- 共24条，每患者3条；
- screen_cases_blind.jsonl不含GT。

Stage2有1条claim的B/C composer同时达到max_tokens导致JSON截断；HTTP200不重跑。A完整N=24，B/C有效N=23，主要paired分析用共同有效23条。

API：
- 142/142 HTTP200；
- 实际费用约¥2.604783 / ¥15 cap；
- reserved未使用。

## 共同有效23条主结果

- A：14/23，PA 60.87%，MCC 0.3006，false-S 0。
- B：15/23，PA 65.22%，MCC 0.1528，false-S 1。
- C：15/23，PA 65.22%，MCC 0.2496，false-S 1。

Paired：
- B vs A：3 rescue / 2 harm，net +1，3名患者；false-S +1。
- C vs A：2 rescue / 1 harm，net +1，2名患者；false-S +1。
- C vs B：1 rescue / 1 harm，net 0。

因此B、C均未达到预注册晋级门槛；C也没有显示出独立于B的retrieval增益。

## 机制线索

B的3个rescue全部只使用原C48：
1. hypotension + aggressive fluid resuscitation；
2. eventually cleared for transfer；
3. right knee immobilizer in extension。

说明“已有候选中的证据聚焦/重组”确实可以改变raw Judge并救回部分病例。

但B也有2个harm：
- C. diff negative被过度裁剪后NS→NA；
- NSURG admission被过度裁剪后S→NA。

另有1条GT=NA被改成S，产生新增false-S。

C没有产生新的净retrieval收益；其两个rescue均已被B覆盖，且B独有的transfer rescue在C中丢失。

## 当前结论

**065不支持当前版本直接晋级。**

但它给出的方向不是“回到后处理”：
- evidence focusing存在真实rescue信号；
- 当前composer最大问题是过度裁剪导致保护证据丢失；
- full eligible-EHR requirement-aware retrieval没有显示独立增益。

下一步若继续前端路线，优先优化“保守的evidence composer / evidence preservation”，而不是继续扩大retrieval范围。
