# 方法与实验设置：论文可用说明

## 核验问题和数据

任务是在已知患者既有EHR下，判断临床陈述为Supported（S，证据支持）、Not Supported（NS，证据不一致）或Not Addressed（NA，当前证据未涉及）。使用VeriFact-BHC v1.1.0已有医生claim-level标签，不新增医学gold。最终实验是valid atomic claim层面的核验，不等于已经验证完整应用中的自由文本切分、定位或临床部署。

003冻结20名探索、40名development、40名reserved。40名development共3675条已用于开发；036的reserved40共3573条（human2292、LLM1281）按原名单完整覆盖。001/002曾有全benchmark汇总，不能声称reserved从未以任何形式接触；本轮前未用其逐例成绩选方法。临床GT在最终参数、请求和GT盲预测封存后才连接评价。

## 固定证据和Judge

原患者EHR按既定目标入院日期范围处理，排除discharge summary，以原paragraph_spans生成可回溯片段：段落以空行分界，长段沿既有640字符/空白边界切分。BM25（k1=1.2、b=.75）与API `Pro/BAAI/bge-m3` dense余弦排序各取前80，dense/BM25交替加入未见ID，形成C48。复用原`Pro/BAAI/bge-reranker-v2-m3` API和原选择代码，最多16个完整片段、每note最多2片段、reference正文与记录头8000字符；外层入院时间头不计入该8000上限。未改成本地BGE。为继承原条件，rerank调用仍基于原A/B/C候选并集（辅助A采用RRF常数60），最终仅从C48选证据。

选择时按rerank降序、passage ID破同分；同日期/类别/原文重复去重。选中片段不再截短，最后按日期、时间、note ID和原始字符起点排序呈现。reference保留note ID、日期及原字符区间，完整实际文本与哈希均可回查。上述是继承的固定证据条件，不声称其等价于原VeriFact作者检索实现。

同期直接Judge B和评分Judge S均为阿里云`deepseek-v4-flash-0731`，原024 prompt/schema，temperature=0、enable_thinking=false、max_tokens=2048。Qwen为阿里云`qwen3.8-27b`，保持024评分配置，仅在DeepSeek的U2改判候选上调用。输入仅原claim和相同reference；GT、作者、BHC和人工诊断不进入Judge。

“普通Judge B”“scoring原始verdict”“scoring score argmax”是三种不同输出。B与S各调用一次；所有后处理共用S，不能把离线方法数当API次数。Qwen API结果不是本地部署、量化、显存或速度实验。

## 决策和概率

三类顺序S/NS/NA，分数为模型声明的0–100整数，和100；不等于从模型内部token logits读取的原生概率。令`z_k=log(max(score_k/100,1e-6))`。

- U0：`argmax(z)`。
- U2：`argmax(z + [2,0,0])`；λ2固定。并列优先NS、再NA、最后S，沿019。
- U2+T：`softmax((z+[2,0,0])/T)`。T仅用development最小NLL拟合，正温度保持U2标签，最终T=4.323675540840898。
- Joint_NLL：原035二参数约束拟合`softmax(a*z+[b,0,0])`，a∈[.05,5]，b∈[0,4a]。全development a=0.23330897008797502、b=0.9332358803519001，λ=b/a=4，命中既定上界。固定U4只作标签核对，不扩大搜索。
- Task_T、Robust_T、MCC_T：原035学习流程与全development冻结参数，仅作既有对照；不根据reserved再选λ。Task/Robust训练折返回2与保护约束相关，不是理论最优常数证明。

API生成参数`temperature=0`与这里的事后温度T是两件事：前者控制生成采样，后者只对已保存score离线重算概率，没有重新调用或修改Judge。

022原标准方法均在035相同训练患者与折划分上拟合，对最终reserved使用全development参数：

|方法|参数/作用|原正则和边界|
|---|---|---|
|Std_T|1个逆温度θ，softmax(θz)，不变标签|.01(θ−1)²，θ∈[.05,5]|
|Std_G|1个S常数偏置|.01θ²，θ∈[−6,6]|
|Std_M|S、NS两个常数偏置，NA为0|.005‖θ‖²，各∈[−6,6]|
|Std_V|3个类别尺度及S/NS两个偏置|尺度以1为中心，.01/3；偏置.005；尺度[.05,5]，偏置[−6,6]|

均保留原022 L-BFGS-B设置。Std_G的历史边界不是为本轮继续搜索λ；与Joint的参数域和正则不同，不能称同一个学习λ实验。Std_T也不同于作用在U2上的无正则U2_T。数值参数见`final_freeze_001/standard_models022.json`。

## A Gate风险控制

仅当`U0!=S且U2=S`时触发。复用033完整development训练的A Gate：原DeepSeek 7维与Qwen 5维score特征，StandardScaler＋固定L2 Logistic。训练允许40人，39人有候选；370候选，训练内患者LOPO确定80%真S保留目标阈值，再全训练拟合。最终阈值0.608679899116368；均值、尺度、系数和截距直接复制，不重新选择患者、阈值或C。

Gate接收原始score特征，不接收温度缩放概率，不包含作者/患者/队列或GT。通过者保留U2的S，拒绝者退回原U0；非候选仍为U0。Qwen核心缺失时事前规定退回U0并单列。Gate概率是候选放行概率，不能当三类核验概率计算NLL/Brier。

12维特征的准确含义（p=原score/100，z使用相同floor）：DeepSeek的pS/pNS/pNA、`zS−max(zNS,zNA)`、`abs(zNS−zNA)`、`−sum(p*log(max(p,1e-6)))`和`U0==NS`；Qwen的pS、同定义S margin、`Q_U0==S`、`Q_U2==S`、`Q_U0==DeepSeek_U0`。尤其non-S margin是绝对值，不是有符号NS−NA差。

原学习配置C=0.1、solver=lbfgs、max_iter=2000、tol=1e−8、l1_ratio=0、random_state=29。训练内LOPO得到每个训练候选的折外概率，将真R概率降序排列，取第`ceil(0.8*R训练数)`个值作阈值，放行采用`>=`，因此并列可超过目标。036不重新训练这套Gate；以上说明其历史拟合规则与冻结参数来源。

## 对照、重复和统计

原VeriFact为002发布R1-70B、100 sentence facts、rerank、absolute_time、current admission、deduplicate=True条件，不是同一C48/同一Judge的组件对照。原系统与当前方法差异同时含检索和判定实现。

R0覆盖全部40人。R1按预先患者ID SHA256排序选4人444条，B/S/Q独立请求，全部固定参数复用；与R0相同claim，不能当新增独立患者。6人重复的保守全任务费用超150，按事前预算规则选4人，非效果驱动。

统一调用002 `evaluate` / `paired_compare`：valid-only三类micro PA（正确比例）、MCC（考虑类别混淆的不平衡关联指标）、AC1（一致性指标），混淆矩阵行GT/列预测。false-S为真实non-S被输出S，其rate分母是真实non-S。分作者和患者报告；配对患者cluster bootstrap1000次，seed0..999共用，区间针对固定预测，未重新训练。多个辅助比较不作p-value筛选。

NLL为真实类负对数概率，Brier为三类平方误差之和（不再除3），越低越好；ECE10用最大类概率的10个等宽桶，仅为分箱描述，另保留classwise可靠性。NLL下降不保证Brier/ECE都改善，更不是临床安全证据。

U0→U2候选中：R是真S救回；H是原正确non-S被改错；W是原错误non-S又变S。净正确增量=R−H；新增false-S=H+W。Gate阻止H可恢复正确，阻止W只降低错误支持而未必变正确；挡掉R会损失正确。

这里“真S/正确”均相对于数据集的医生GT，不是036新增医学判断。降低false-S本身也不证明Gate优于降低全局λ的所有风险工作点；本轮将Gate定位为冻结工作点的实际风险—性能及成本权衡，不宣称新的Pareto最优。

## 缺失和费用

所有HTTP原回执保存，200不为格式或答案重新生成。非核心reason/checks异常不中止；核心非法或冲突单列。主评分缺失不伪造U0；报告完整冻结N、每方法覆盖、missing ID、共同有效主分析与全N missing-as-error PA敏感性。原reason不因λ/Gate改判重写，因此最终标签与原解释可能不一致，不宣称已经形成完整可部署解释系统。

评价对象是医生claim-level标签，没有新增passage-level evidence gold。标签改对不等于已经证明C48中每条改判的支持证据充分、引用完全正确；既有C48信息损失也没有被后处理自动消除。因此本轮可以支撑判定性能与风险权衡结论，不能直接扩展为证据忠实性或临床应用有效性已经验证。

本轮特殊上限150元；公开峰值无缓存价格估算DeepSeek3/9、Qwen3/12、Pro BGE0.07元/百万tokens，未知请求保留费用上界，尚非账单核销。环境统一`research-verifact-029`经`run_research.ps1`启动。请求、回执、usage、模型返回、重试及费用记录均保留，不改变历史环境或API政策。

价格核实来源：[阿里云DeepSeek0731](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)、[阿里云Qwen价格表](https://help.aliyun.com/zh/model-studio/model-pricing)、[硅基流动Pro BGE价格](https://siliconflow.cn/pricing)。未用更便宜的DeepSeek泛化别名价格冒充0731快照；低谷/缓存优惠未用于放宽任务预算。
