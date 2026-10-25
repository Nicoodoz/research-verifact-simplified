# 034 extension: boundary and confidence separation

Current conversation authorizes task034. The existing three-way comparison and the concurrently renamed task035 directory are preserved. Offline numerical data only; no API or reserved patients.

## 研究问题与方法
主要比较六种方法：U0、固定U2、U2+T、联合NLL尺度与S偏置、任务目标选择lambda+T、患者稳健选择lambda+T。
q=softmax((z+lambda*eS)/T)，z=log(max(score/100,1e-6))。T>0只改变概率，不改变固定lambda的标签；平分沿NS、NA、S。
U2+T以固定lambda=2拟合beta=1/T；无正则化NLL，beta范围[0.05,5]。
联合NLL拟合(a,b)，q=softmax(a*z+b*eS)，a范围[0.05,5]、0<=b<=4a，等价lambda=b/a在[0,4]，与任务选择法具有相同最终参数空间。保留边界命中记录。
任务lambda：在[0,4]训练评分的精确切换区间代表点及0/2/4上评价；候选需训练PA>=U2且训练false-S<=U2，然后最大化训练MCC。相同预测保留2（若可用），否则区间代表点；同指标并列依次较低false-S、较接近2、较小lambda。
稳健lambda：相同候选与约束，以256次训练患者cluster重抽的MCC差（相对U2）第10百分位最大为目标；再以训练MCC及相同平分顺序选择。它是开发选择分数，不是置信保证。
两个任务选择法在固定lambda后，按相同NLL规则拟合T；U2始终是可行回退。训练约束不保证留出患者同样满足。
辅助比较直接复用022的G/M/V/T：原NLL单偏置、多类偏置、vector scaling、温度缩放，保留原正则化及边界，不能将它们与新方法的差异全部归因于目标函数。

## 数据与评价
A：022原1529条R0拟合，沿原4折患者划分；R1的879条仅评价，绝不参与拟合。复现原U0/U2和G/M/V/T标签、指标，并按原U2正确/错误、真类0分、近边界等固定分组分解NLL。
B：033全部40名development、3675条评分。原16人沿022折号，其余24人按固定哈希排序均分4折，每折10人；同一患者全程只在一个外层折。任何拟合不使用其评价患者。
C：024 DeepSeek/Qwen同879条，沿同一患者折号。各模型用自身非留出患者拟合；另将源模型同患者范围的参数直接迁移给目标模型留出患者，两方向均报，区分参数迁移与规则迁移。无新增推理。
所有方法共用相同评分与评价ID。公开主要表为B的all/human/llm；A为复现/重复，C为小样本迁移辅助，不将各材料或轮次当新增独立患者。
分类统一调用002 evaluate/paired_compare；概率报NLL、三类Brier、10箱top-label ECE（仅辅助）与逐类可靠性。报告三类召回、false-S数及真实非S分母、R/H/W、逐患者与等权敏感性。
主配对：B中U2+T对U2的NLL；稳健对固定U2的PA/MCC/false-S；稳健对任务lambda、联合NLL。1000次配对患者bootstrap，固定已有OOF预测，不覆盖完整重拟合不确定性；其余为辅助，不做事后显著项筛选。
保存各折拟合ID、参数、候选状态、选择分数、预测和输入/代码哈希。执行完成再合并评价，不按结果修改配置或重抽患者。最终可保存全development拟合参数，但不在训练本人上报泛化。

## 交付
中文报告、统一指标表、配对区间、分层与重复/迁移结果、参数稳定性及少量PNG/SVG图、复现与自检入口；不冒充独立审计，不自动提交/推送。034正式文件保持字节不变，并保存来源指纹用于核对。
