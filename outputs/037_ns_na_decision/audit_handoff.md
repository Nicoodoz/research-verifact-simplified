# 037交审入口

执行者自检通过不等于独立审计。任务在036之后由用户明确授权；研究动机来自已公开的036分析，因此全部新结果均限定为development探索。

## 重点检查
1. run_001/freeze.json记录方法、起始HEAD、源数据/代码指纹；prediction_freeze.json先于分析输出。
2. 数值输入仅main40和old_R1，均为003 development患者，3675/879条；不读取036 reserved逐例文件。
3. 四个外层患者折。阈值由外层训练材料内3折预测选择；每个内层Logistic的训练特征另由剩余两折校准器互留出产生。
4. 每一级训练/评价患者及ID存在fits账本。Logistic使用的真实NS/NA标签只用于各自允许的训练集，没有把误拒的S重标为NA。
5. Std_M/Std_V沿022原拟合实现。main40的原U0/U2/M/V标签复现036 development结果；baseline_replay.json提供概率差。
6. 三种修复只做V原NA→NS；原S和原NS保持，NLL/Brier沿用未修改的V概率。新标签可能不是概率argmax。
7. 主比较为Ratio−VM和Logistic−Ratio；002统一指标与1000次患者bootstrap。附97.5%区间仅覆盖两项主比较，不保证全部辅助检验。
8. 概率和分类指标分开；fixed预测bootstrap未重训，不包含全流程训练不确定性。
9. 排序曲线、同NS的混合包络、同分冲突oracle是GT知情诊断，不用于选择外层工作点或部署。
10. Logistic与VM在3675/879两视图逐条同标签；结果不支持扩大模型，未据结果追加配置。

## 复查
使用tasks/037_ns_na_decision/verify037.py，指定新的输出文件；原verification_001.json不覆盖。
主报告report.md、机读表run_001/main40/、冻结源码run_001/source/、参数run_001/fits/。
037没有重新训练全40部署版本，没有对reserved重跑，没有提交/推送。
工程上传诊断见engineering_notes.md，不影响科学运行。后续仅独立审计或用户另行安排，不自动038。
