# 054：PriorG under Unlabeled Label Shift

054回答部署问题：新环境类别比例改变、但没有目标域标签时，PriorG怎么办？

方法固定053的T-S+PriorG，不搜索新bias/阈值；在052/053两批不重叠claim上构造pure label shift，比较Frozen、Oracle、BBSE、EM PriorG以及U2/Gate A/原VeriFact。BBSE/EM目标域只读无标签预测或score。

结果：BBSE能较好估计target prevalence，且误差随无标签batch增大而下降；但把估计prior自动应用到当前PriorG并不能稳定提高分类。甚至Oracle真实target prior也多数不改善PA/MCC，说明LLM自报score不足以直接作为可靠posterior做动态Bayes修正。

建议冻结PriorG作为默认，BBSE作为shift monitor；明显shift触发少量人工目标标签重新校准，而不是自动更新prior。

正式报告：`../../outputs/054_unlabeled_prior_shift/report.md`；状态：`CURRENT_STATUS.md`；核验：`verification_001.json`。0 API，未自动commit/push。
