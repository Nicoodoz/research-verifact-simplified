# 054：PriorG under Unlabeled Label Shift

## 研究问题

审稿人可能质疑：PriorG依赖类别先验；如果部署环境的Supported / Not Supported / Not Addressed比例发生变化，而目标域没有人工标签，系统还能否适配？

054只回答这个问题，不再搜索新的分类bias、阈值、作者路由或prompt。T-S、G参数与当前PriorG公式全部冻结。

核心假设是经典label shift：目标域类别比例P(Y)变化，但类条件模型行为近似稳定。通过按GT分层重采样现有病例构造目标域，因此模拟本身严格满足label-shift构造；这不代表一般covariate/concept shift也能被无标签适配解决。

## 数据

使用两批已有、具体claim不重叠的development内部材料：
- 052：240条，其中T-S score有效236条；
- 053：240条，其中T-S score有效237条。

两批交叉使用：模拟052为target时，BBSE混淆矩阵只由053带标签样本估计；模拟053为target时，反之。目标域标签仅用于构造已知prevalence的模拟批次和最终评价，不提供给BBSE或EM估计器。

当前source prior固定为053冻结PriorG使用的031材料池比例：S=1108、NS=100、NA=170。T-S G和calibration prior也完全复用053冻结值。

## 方法

比较7种方法：Frozen PriorG、Oracle PriorG、BBSE PriorG、EM PriorG、U2、冻结Gate A、原VeriFact。

Frozen PriorG始终使用source prior。Oracle PriorG使用模拟目标域真实prior，只作为上限。BBSE用source混淆矩阵和target无标签hard prediction分布估计target prior。EM用Frozen PriorG soft posterior在target无标签批次上估计target prior。

Gate A在052和053均从已保存DeepSeek/Qwen分数离线重算同一冻结模型，避免两批Gate口径不同。

BBSE使用三类simplex约束最小二乘；EM初始化source prior，迭代reweight Frozen PriorG posterior。两者都不读取目标GT。

T-S score无效病例不参与prior估计；部署分类若遇到无效T-S，沿053固定语义fallback到同期N-S U2。模拟label-shift主分析只对T-S score有效池重采样，以隔离prior适配机制；无效率另外报告。

## 模拟目标prior

固定6种环境：source prior、high-S 90/5/5、70/15/15、60/20/20、NS-heavy 60/30/10、NA-heavy 60/10/30。

无标签adaptation batch size分别为60、120、240、480。每个target pool × prior × batch size做500次确定性bootstrap；每次另抽独立240条evaluation batch。抽样有放回，保持类内病例/score分布不变，因此只改变P(Y)。

## 评价

prior估计：各类估计比例、L1 prior error、BBSE混淆矩阵condition number、EM收敛。

分类：PA、MCC、false-S（240条中的平均计数）、S/NS/NA recall，并报告相对Frozen PriorG的配对变化。U2/Gate A/原VeriFact只作为固定系统参照。

054为0 API实验，不修改PriorG主系统，不使用reserved，不自动commit/push。
