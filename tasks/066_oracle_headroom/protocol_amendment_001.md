# 066 Amendment 001：Single GT-aware Evidence Oracle

## 原因

预检显示历史正式候选池可为39个053基准错误中的36条重建C48，且同患者eligible-EHR corpus可跨历史冻结任务回查。任务目标是测上限而不是筛新部署方法。

因此不再分别收费执行E1/E2；避免重复Qwen/DeepSeek调用。

## 最终Evidence Oracle

对39个Frozen PriorG错误逐条：
1. GT-aware planner看到claim与医生GT，仅用于提出最有信息量的verification requirements/search queries；
2. 在该患者目标住院的冻结eligible EHR corpus上做本地BM25高召回；
3. 取top32候选，并将可重建的历史C48全部并入候选（长候选时优先保留C48+BM25 top）；
4. GT-aware composer知道GT，但只能选择3–8个真实原始passage，必须保留会改变限定条件的重要反证；
5. 最终T-S thinking-high Judge只看到claim + 选中的raw EHR reference，绝不看到GT、planner或composer文字；
6. 再机械套053 Frozen PriorG。

## 前处理瓶颈归因

若Evidence Oracle把基准错误修对：
- selected passages全部在历史C48内：记为 C48_selection_composition_headroom；
- 至少一个决定性selected passage在C48外：记为 retrieval_headroom；
- C48不可重建但full-EHR修对：记为 upstream_headroom_unlocalized。

若oracle pack后T-S+PriorG仍错：记为 evidence_oracle_failed_to_fix，主要提示推理/GT-scope残余，但不证明证据绝对完美。

原protocol中的Reasoning Oracle与Combined Oracle定义不变。

hard cap仍为20元；不使用reserved；不自动commit/push。
