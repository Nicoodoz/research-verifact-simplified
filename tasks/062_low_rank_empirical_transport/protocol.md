# 062：Low-rank Empirical Transport for Zero-label Judge Drift

## 目标

061已经排除“只要固定target prior就够”的解释：
- BBSE真实prior L1仅约0.023/0.031；
- Oracle-fixed仍不能稳定恢复12维class-specific drift；
- 甚至synthetic真实无漂移时，Gaussian latent mixture仍产生明显伪漂移。

062因此同时更换两件事：

1. 把3×4=12维自由class-specific drift压成低秩结构；
2. 去掉Gaussian latent mixture，不再给target逐条猜latent GT，而是直接匹配**经验分布**。

主方法是 rank-1 empirical transport；rank-2只作上限/必要性诊断。

## 输入表示

每条claim使用4维联合log-odds：
- DeepSeek: u_DS,S, u_DS,NS
- Qwen: u_Q,S, u_Q,NS

沿用059–061：
- score统一加0.5 pseudo-count；
- u_S = log((score_S+0.5)/(score_NA+0.5))
- u_NS = log((score_NS+0.5)/(score_NA+0.5))

对每个source方向只用source全体均值/标准差做z-score。

## Prevalence sensor

target prior固定为Frozen PriorG + BBSE估计。
沿用061实现：
- source GT confusion matrix；
- target只用Frozen PriorG hard predictions；
- constrained simplex least squares估pi_hat。

不在062中重新联合优化prior。

## Empirical transport

source有GT，所以保留三类真实经验样本集合：
Z_S, Z_NS, Z_NA。

不假设Gaussian。

对每类y施加一个z-space平移delta_y，得到：
Z_y' = Z_y + delta_y。

用RBF Random Fourier Features近似经验kernel mean：
mu_y(delta_y) = mean phi(Z_y + delta_y)。

target无标签经验mean embedding：
mu_t = mean phi(Z_target)。

固定BBSE prior后，拟合：
min || mu_t - sum_y pi_hat(y) mu_y(delta_y) ||^2。

RFF设置固定：
- dim=128；
- bandwidth=source标准化4维样本两两距离的非零中位数；
- W/b只由source tag和固定seed生成。

## Rank-1结构

主模型：
delta_y = a_y * v

其中：
- a_y：三个类别各一个幅度；
- v：4维共同漂移方向；
- ||v||=1。

因此不是12个自由参数，而是约6个有效自由度。

优化：
- scipy L-BFGS-B；
- a_y限制[-3,3]（source-z单位）；
- v原始参数限制[-2,2]，目标函数内归一化；
- 固定2个deterministic starts：1个由no-shift点目标梯度的top rank-1 SVD方向初始化，1个固定seed随机方向；
- 选择训练子集RFF residual最低解；
- 不根据062结果调bounds、starts或kernel。

## 无漂移防伪：fit/holdout + source-null calibration

每个target batch按固定hash/index分成两半A/B。

分别：
- A拟合rank-1，B评价；
- B拟合rank-1，A评价。

定义heldout gain：
gain = mean(no-shift residual - transported residual)。

只有gain超过source-only null的95%阈值才接受drift，否则最终delta=0。

null阈值：
- 从source按同一固定prior、同一batch n有放回重采样；
- 无任何drift；
- 每个source/prior/n固定10个null batch；
- 对每个null batch执行完全相同的双向fit/holdout流程；
- threshold=q95(null gain)。

这一步专门防止061出现的“真实无漂移却估出漂移”。

## Rank-2诊断

rank-2不是主部署方法，仅用于判断rank-1是否表达力不足。

delta = A @ V^T，
其中A为3×2，V为4×2；V在目标函数内QR正交化。

只在：
1. 两个真实052↔053方向；
2. synthetic mixed、n=960（每source/prior固定3次）；
3. 对应source-null实际batch校准（每条件5个null batch）

上运行。

rank-2同样必须通过holdout/null校准；不能仅看训练fit。

## Synthetic

沿用060/061四种prior：
- source
- 60/20/20
- 60/30/10
- 60/10/30

batch n=240/480/960。

drift：
- none
- NS_QNS
- NA_DSS
- NS_DSNS
- S_QS_down
- mixed

前四个单一非零class×feature以及S_QS_down都是rank-1真值；
mixed用于测试rank-1不足时rank-2是否有额外价值。

每条件5次正式评价。
null calibration每source/prior/n为10次，独立seed流。

主要指标：
- none false-accept rate；
- 非none accept/detection rate；
- rank-1真值pattern的**active-coordinate delta MAE**（避免12维平均把单一漂移误差稀释）；
- inactive-coordinate spurious MAE；
- 非零漂移sign accuracy；
- heldout gain。

## 真实052↔053

GT-blind阶段先冻结：
- BBSE prior；
- rank-1 null q95；
- rank-1 heldout gain / accept；
- 若accept，full-target rank-1 delta；否则delta=0；
- rank-2同类诊断结果。

actual_unlabeled.csv写入并记录SHA256后，才读取target GT评价：
- true prior与BBSE L1；
- true 3×4 class mean shift；
- true shift SVD rank-1/rank-2 explained energy；
- rank-1/rank-2估计delta的weighted R2、MAE、sign accuracy；
- 与061 fixed-Gaussian R2比较。

## 事前判读

主rank-1方法要被视为“解决061伪漂移问题”，至少需要：
1. n=960 synthetic none false-accept <=10%；
2. n=960四个rank-1真值pattern（NS_QNS / NA_DSS / NS_DSNS / S_QS_down）平均accept >=80%；
3. 这些rank-1真值pattern n=960 active-coordinate delta MAE <=0.30；
4. sign accuracy >=90%。

真实方向：
- 若rank-1两方向R2均>=0.50且均通过holdout/null accept，可进入下一步dynamic decision研究。
- 若rank-1未过，但rank-2两方向均通过null accept且R2>=0.50，则结论为“rank-1表达不足，rank-2值得后续正式化”。
- 若rank-2也不能过，则当前“平移型低秩经验transport”仍不足，应停止继续堆同类参数。

## 边界

- low-rank假设由059–061后的GT诊断启发，因此真实052/053上的R2仅作development诊断，不能算独立外部验证。
- rank-2是诊断上限，不作为当前正式部署机制。
- 0 API，不使用reserved，不自动commit/push。
