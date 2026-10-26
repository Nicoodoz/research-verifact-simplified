# 064：Target-local Safe Policy Selection

064把问题从“恢复完整target Judge reliability”改成“认证Frozen PriorG附近的局部policy”。

候选policy：BASE、Qwen强non-S veto（V80/V60）、Qwen高置信S rescue（R90）及组合。少量target标签只学习policy disagreement region，不重建分类器；证据不足回退BASE。

Oracle诊断：
- 052→053正确policy是R90（+5 correct，MCC 0.5596→0.5905，false-rescue 16.7%）；
- 053→052正确policy是BASE（R90风险66.7%）。

最终patient-disjoint Exposure Fix结果：
- 052→053 active 10 labels：R90认证58%，unsafe 0%，future ΔPA +1.06pp、ΔMCC +0.0127；
- 053→052 active 20 labels：BASE fallback 90%，unsafe 10%；
- 尚未达到两方向同时通过的预注册门槛，因此missing link未正式闭合。

关键新诊断：R90 region只有6条/6患者。当前瓶颈不是总label budget，而是稀有action-region标签证据不足。

29项executor verification PASS；0 API；未使用reserved；独立审计未执行。
