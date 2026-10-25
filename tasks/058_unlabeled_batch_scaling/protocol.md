# 058：Unlabeled Batch-size Scaling

## 目标
检验057 soft detector的主要瓶颈是否只是target无标签batch太小。

## 固定方法
完全复用057主方法，不改特征、RFF维度、bandwidth、BBSE、阈值定义或H0/H1构造。

## Batch size
n = 240, 480, 960, 1920, 3840。

## 评价
- 两个source方向：052→053、053→052。
- 六种prior场景沿用057。
- 每条件1000次H0用于95%阈值；H0/H1各500次评价。
- 汇总每个n的平均H0 false-alarm和平均H1 detection。
- 同时报告每种prior场景，识别是否存在即使大n仍难检测的shift。

## 判读
- 若两方向在某个n均达到 mean H1 detection >=90% 且 H0 false-alarm <=10%，说明主要瓶颈可被更大无标签batch缓解。
- 若到n=3840仍有方向明显低于90%，或特定shift长期难检测，则存在不只是样本量的结构性可识别性问题。

## 边界
n>现有236/237真实池时通过类内有放回重采样模拟，只说明在当前经验分布下增加独立观测的统计趋势，不等价于已有236条claim复制后就获得更多真实信息。
0 API，不使用reserved，不修改057。
