# 077 结果入口

077零API判别检查完成：B/F4去重共同有效262条、16患者；最早/最晚平均类别对AUC差+0.0040/−0.0044，无全面排序改善。0–20%错误支持率预算下经验混合包络平均PA差+3.75/+4.06个百分点，患者区间跨0；两口径逐患者及任务块留出仍正，但075/80606影响大，LLM方向不稳。仅保留F4低风险工作点的有限验证价值，不升级默认、不再改示例、不重启通用自适应。0元、0拟合，自检PASS，独立审计未执行，不自动078、不提交推送。

[主报告](report.md) · [数字附录](numeric_appendix.md) · [同风险曲线](frontiers.svg) · [AUC图](auc_differences.svg) · [论文表述](paper_paragraph.md) · [冻结口径](../../tasks/077_static_example_discrimination/README.md)

复现：用项目环境运行`tasks/077_static_example_discrimination/analyze077.py --output outputs/replays/077_<唯一运行名>`，目标目录须不存在。`verify077.py`检查已生成的正式077曲线；`render077.py`生成表图；`finish077.py`更新当前说明文档并封存。均无API，无模型拟合。
