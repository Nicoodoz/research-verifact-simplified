# 037：固定Supported集合的NS/NA决策研究

## 授权和范围
用户明确授权执行037；本任务承接“Std_V概率保留、Supported判定固定、专门研究NS/NA”方案。
仅使用已有development评分与医生标签，0 API、0费用。不得读取036 reserved逐例数据、重新评价新方案在reserved上的效果，或据其选择参数。
037由036后的事后观察引出，属于新的探索性development研究；不改写036冻结结果，不声称新的独立最终验证。
原始数据、001—036结果、环境、.gitignore保持；不自动提交、推送或续开038。

## 固定设计
主队列为035 main40的3675条、40名development，沿035四个患者折。
U0/U2以及022原Std_M、Std_V为参照；M/V沿原正则、边界和优化器。外层仅用其他30人拟合。
所有修复方法保持外层Std_V的S预测及原NS预测，只允许原NA改为NS；S召回、S精确率、false-S应逐条不变。
新增三种固定比较：
1. VM_switch：V=NA且M=NS时改NS，不学习路由阈值。
2. Ratio_restore：原V=NA中用r=q_NS/(q_NS+q_NA)排序，阈值只在外层训练患者的严格内层预测上确定。
3. Logistic_restore：四维低容量Logistic，对原始NS-NA log差、S竞争margin、V的NS-NA log差、V=NA且M=NS指示建模。
Logistic为StandardScaler+L2、C=0.1、max_iter=2000、tol=1e-8、固定seed37；不搜索分类器/超参数。
Logistic只以训练侧折外V非S且真实NS/NA的样本拟合NS vs NA；真实S不改标，全部保留在系统评价和阈值选择分母中。

## 阈值目标与嵌套
目标不是在验证集找最高值：以相同内层预测上的VM_switch真实NS检出数为恢复目标，达到该目标的阈值中最大化全样本正确数；并列优先NA正确数、MCC、较少改判。
Ratio只降低原NS/NA门槛至[0,0.5]；Logistic阈值覆盖[0,1]及全不改状态。并列分数整体放行，不拆同分样本。
外层训练有3个旧折；每次内层留一旧折，校准器和Logistic均排除它。Logistic训练用剩余两个旧折互相留出生成的校准器预测，避免元特征间接读到内层验证标签。
最终外层Logistic用30名训练患者的3折校准器折外特征拟合；所有阈值由上述内层预测选择，再应用外层10人。保存各级训练/评价ID及参数。
固定附加诊断：把同一外层模型应用于old_R1的对应留出患者评分，检查评分轮次变化；不重新拟合、不作为新患者确认。
所有规则和代码在读取新037评价结果前封存。三种方法一次性全部报告，不因结果添加新配置。

## 评价与停止
沿002 evaluate/paired_compare；全3675条，all/human/LLM、患者方向、PA/MCC/AC1、三类PRF、false-S、R/H/W式NA→NS救回/误伤账本。
主要比较Ratio_restore−VM_switch，以及Logistic_restore−Ratio_restore；各报患者配对1000次bootstrap，附两比较97.5%区间作为敏感性，不把多条件最优点当确认结论。
同时报告相对Std_V、Std_M的变化；固定Std_V概率仅代表未变的基础概率预测，新决策并非概率argmax，不用最大概率充当新决策置信度。NLL/Brier保持基础V值，不宣称重新校准。
保存NS/NA排序曲线与相同NS检出数下的NA保留诊断（GT知情、只用于描述），不从外层曲线重选阈值。
统计原V非S中可救回NS上限、原V的S错误遗留，以及同一折内相同原始score的NS/NA冲突，界定仅靠score的能力上限。
学习器不能稳定超过固定切换/单阈值则不推荐增加复杂度；不追加文本、第二Judge、NLI或作者专属模型。
输出中文报告、设置/数值表、所有患者外预测与嵌套账本、少量图、自检及交审入口。完成后停止。执行者自检不冒充独立审计。
