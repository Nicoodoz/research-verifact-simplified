# 052：First-tier Same-cohort Validation and Thinking-score Optimization

## 核心结论

052把036之后最有希望的 N-V、T-S+U2、T-V 与 U2、患者外Gate A 放到同一批24名development患者、240条GT盲hash抽样claim上比较，并测试只用051另外16名患者拟合的N-S/T-S G/M校准。

本轮最重要的结果是：

> **051里N-V/T-V的总体accuracy优势没有在新的24名患者上复现；真正跨患者保留下来的第一梯队信号是 T-S + 固定U2。它没有明显提高总体PA，但显著减少false-S、提高NS/NA识别和MCC，并在human-written claims上呈现更强的净收益。**

240条样本实际GT构成为S=191、NS=18、NA=31；human=135、LLM=105。这是每患者固定10条、不按GT筛选的patient-balanced development随机样本，不是三类均衡集，也不是reserved/external test。

### 主结果

| 方法 | 有效N | correct/240* | PA(valid) | MCC | false-S | S/NS/NA recall |
|---|---:|---:|---:|---:|---:|---|
| 原VeriFact | 240 | **195** | **81.25%** | 0.4949 | 12 | 90.05 / 55.56 / 41.94% |
| U2 | 240 | 190 | 79.17% | 0.4464 | 13 | 88.48 / 27.78 / 51.61% |
| Gate A patient-out | 240 | 187 | 77.92% | 0.4504 | 10 | 86.39 / 33.33 / 51.61% |
| N-V | 240 | 181 | 75.42% | 0.4608 | 6 | 81.68 / 66.67 / 41.94% |
| T-S raw | 236 | 177 | 75.00% | 0.5058 | **3** | 75.39 / 50.00 / 77.42% |
| **T-S + U2** | 236 | **188** | **79.66%** | **0.5435** | **5** | 81.68 / 44.44 / 77.42% |
| T-V | 238 | 175 | 73.53% | 0.4806 | **3** | 75.39 / 50.00 / 70.97% |

* correct/240把核心无效输出按未判对计；PA/MCC列按各方法有效输出计算。T-S有4条核心无效，T-V有2条。

在T-S/U2共同有效的236条上，T-S+U2相对U2为 **21 rescue / 20 harm，净+1，false-S -8**；ΔPA +0.42个百分点，95%患者bootstrap区间[-4.66,+5.20]；ΔMCC +0.0927，区间[-0.0144,+0.1872]。因此不能宣称PA/MCC已稳定提高，但风险/类别结构明显改变。

## 1. 相对Gate A：T-S+U2是本轮最清晰的正向比较

Gate A按原029/033配方重建，但对每个052患者严格排除该患者；fresh N-S的22个U0→U2候选才调用Qwen，22/22有效。Gate保留15/22翻转。

在T-S有效的236条共同集合上：

- T-S+U2 vs Gate A：**21 rescue / 17 harm，净+4**；
- false-S再减少 **5条**；
- ΔPA +1.69个百分点，95%患者区间[-2.55,+5.96]；
- ΔMCC **+0.0894，95%区间[+0.0020,+0.1690]**。

因此，在这批development患者上，T-S+U2相对患者外Gate A同时显示：正确数点估计更高、false-S更少、MCC更高。PA增益仍不确定，但MCC配对患者区间为正。

这与036的风险控制故事不同：Gate A依靠第二Judge筛U2翻转；T-S+U2则先改变Judge的推理模式，再使用原固定λ2，没有Qwen Gate。

## 2. operational sensitivity：T-S核心无效时退回同期U2

正式052规则把T-S核心无效记为missing，不事后替换。4条T-S核心无效中：
- 3条是输出包含verdict但缺少label_scores；
- 1条thinking耗满8192 tokens，最终content不是完整JSON。

作为明确标注的部署敏感性分析，若仅在这4条无效时退回同期冻结U2，不改变任何有效T-S预测：

| 方法 | correct/240 | MCC | false-S | S/NS/NA recall |
|---|---:|---:|---:|---|
| U2 | 190 | 0.4464 | 13 | 88.48 / 27.78 / 51.61% |
| Gate A patient-out | 187 | 0.4504 | 10 | 86.39 / 33.33 / 51.61% |
| **T-S+U2, invalid→U2** | **191** | **0.5399** | **5** | 83.25 / 44.44 / 77.42% |

该fallback相对U2：21 rescue / 20 harm，净+1，false-S -8，ΔMCC +0.0935，95%患者区间[-0.0141,+0.1868]。

相对Gate A：21 rescue / 17 harm，净+4，false-S -5，ΔMCC **+0.0895 [0.0027,+0.1678]**。

患者正确数方向：
- vs U2：11名患者正向、8负向、5持平；
- vs Gate A：10正、6负、8平。

这是post-hoc operational sensitivity，不替换052主结果，也不是重新调λ；它只展示实际部署中对结构无效回答采用固定基线fallback后的完整覆盖表现。

## 3. Human-written claims：T-S+U2的信号更强

本240条中human=135：S=88、NS=16、NA=31；LLM=105：S=103、NS=2、NA=0。LLM组极度偏Supported，因此更保守的thinking路线在总体correct上天然付出较大代价。

Human子组点估计：

| 方法 | correct/135* | valid PA | MCC | false-S | S/NS/NA recall |
|---|---:|---:|---:|---:|---|
| 原VeriFact | 99 | 73.33% | 0.5001 | 10 | 86.36 / 62.50 / 41.94% |
| U2 | 95 | 70.37% | 0.4421 | 11 | 84.09 / 31.25 / 51.61% |
| Gate A patient-out | 94 | 69.63% | 0.4536 | 8 | 81.82 / 37.50 / 51.61% |
| N-V | 92 | 68.15% | 0.4836 | 4 | 76.14 / 75.00 / 41.94% |
| **T-S+U2** | **101** | **76.52%** (132 valid) | **0.5928** | **3** | 78.41 / 50.00 / 77.42% |
| T-V | 92 | 69.17% (133 valid) | 0.5089 | **2** | 70.45 / 50.00 / 70.97% |

若T-S无效时回退U2，human为 **103/135、MCC 0.5877、false-S=3**。

Human-only患者cluster配对中，该fallback相对：
- U2：ΔPA +5.93pp，95%区间[-3.85,+14.09]；ΔMCC +0.1456 [-0.0062,+0.2700]；
- Gate A：ΔPA +6.67pp [-1.61,+13.60]；ΔMCC **+0.1341 [0.0041,+0.2426]**；
- 原VeriFact：ΔPA +2.96pp [-5.64,+11.43]；ΔMCC +0.0877 [-0.0762,+0.2238]。

因此，052对“human-written BHC更难”的原论文局限提供了一个值得重视的新信号：thinking scoring + U2在human claims上同时提高balanced discrimination、显著减少错误支持，并在点估计上超过原VeriFact/U2/Gate A；但PA区间仍宽，不能视为最终确认。

LLM子组因为103/105都是真S，原VeriFact/U2依靠高S召回获得更高PA；T-S+U2较保守，因此correct较低。这个作者差异解释了为什么全240条总体PA没有像human组一样明显提高。

## 4. 051学习的G/M校准没有迁移；旧U2反而最好

052事前只用051的16名患者（N-S 144条平衡S/NS/NA；T-S 143条有效）拟合与022完全相同的低容量G/M配方，评价24名患者完全不参与训练。

学习参数本身已经显示score分布改变：
- N-S G的Supported bias约 -0.934；M约[-1.711,-0.980]；
- T-S G约 +0.134；M约[-0.247,-0.732]。

但在052上，T-S G/M的最终标签与T-S raw完全一致：177/240按missing-as-error、MCC 0.5058、false-S=3，明显低于T-S+固定U2的188/240、MCC 0.5435。

N-S G/M也只有179/240，低于固定U2的190/240。

这说明051的类别均衡训练分布上最小化NLL得到的边界，并没有转化为052的patient-balanced自然偏斜样本上的分类优势。**thinking的正信号不是“任何重校准都更好”；目前最能跨样本保留效果的仍是简单固定λ2。**

因此052不支持继续基于这批评价数据微调新λ、G/M或更复杂校准器。

## 5. 选择性cascade没有复现，停止当前版本

051已有输出上，N-V判S后交给T-S/T-V复核曾出现漂亮的离线组合信号。052把同样规则原样带到新24名患者，结果没有复现：

| 方法 | correct/240 | MCC | false-S |
|---|---:|---:|---:|
| N-V | 181 | 0.4608 | 6 |
| N-V→T-S+U2 | 171 | 0.4299 | 4 |
| N-V→T-V | 166 | 0.4290 | 2 |

N-V→T-S+U2相对N-V为0 rescue / 10 harm；N-V→T-V为1 rescue / 16 harm。相对U2，两者分别净少19和24条正确。

所以051的cascade组合属于小样本偶然/队列依赖信号，052明确反证了“只复核N-V的Supported即可稳定改善”的假设。当前不继续调cascade触发条件。

## 6. N-V / T-V总体accuracy优势也没有复现

在052新24名患者：
- N-V：181/240，MCC 0.4608，false-S=6；相对U2 9 rescue / 18 harm，净-9；
- T-V：175/240（238 valid），MCC 0.4806，false-S=3；相对U2共同238条17 rescue / 30 harm，净-13，ΔPA患者区间上限已低于0约-0.42pp。

因此051 balanced 96条上N-V=67/96、T-V=65/96的overall accuracy优势不能外推到自然偏S的patient-balanced样本。它们仍然是低false-S工作点，但不是目前替代U2的overall性能路线。

T-V还有2/240条thinking耗满8192 completion tokens并留下不可解析最终JSON；固定12条repeat中T-V有2次标签变化（83.3%一致），而N-S/N-V/T-S raw均12/12一致。

## 7. 原VeriFact：总体PA仍然很强，但错误结构不同

同240条上原发布系统v1.1.0-rater-121为195/240、PA81.25%、MCC0.4949、false-S=12，是本轮总correct最高的系统。它的优势主要来自高Supported recall 90.05%，且NS recall 55.56%；NA recall只有41.94%。

T-S+U2（invalid→U2 sensitivity）为191/240、MCC0.5399、false-S=5，S/NS/NA recall为83.25/44.44/77.42%。相对原VeriFact：24 rescue / 28 harm，净-4；ΔPA -1.67pp，95%患者区间[-7.50,+4.17]；ΔMCC +0.0450，区间[-0.104,+0.163]；false-S -7。

因此052不支持“当前系统在自然偏斜development样本上总体全面超过原VeriFact”。更准确的是：原VeriFact保持更高PA；T-S+U2形成更低false-S、更高NA recall和更高MCC点估计的不同风险/类别工作点。Human-written子组则出现T-S+U2点估计超过原VeriFact的信号。

## 8. T-S+U2稳定性

12条事前hash repeat：
- N-S U2：12/12标签一致；
- N-V：12/12；
- T-S raw：12/12；
- **T-S+U2：11/12（91.7%）**；
- T-V：10/12（83.3%）。

唯一T-S+U2变化为同claim从Not Supported跨λ边界变Supported。说明thinking raw仍很稳定，但label_scores+λ仍保留一定边界波动；不过本小重复集优于050中三次聚合的不稳定表现。12条仍不足以证明全队列重跑稳定性。

## 9. 成本

052共1030次API，1030/1030 HTTP200，usage估算总费用 **¥19.369866 / ¥80 cap**：
- N-S主240：¥2.996931；repeat12：¥0.145599；
- N-V主240：¥2.833662；repeat12：¥0.138111；
- T-S主240：¥6.267072；repeat12：¥0.300966；
- T-V主240：¥5.996577；repeat12：¥0.307905；
- Gate Qwen候选22：¥0.383043。

若部署T-S+U2，核心Judge调用成本在本样本约为N-S scoring的2.1倍；但不需要Gate A的Qwen第二Judge。invalid→U2 fallback若按需触发，只需在少量T-S结构失败时再调用基线，而不是所有claim双跑。

## 10. 完整性与执行边界

Executor verification共 **7261项PASS**：
- 24名评价患者与051的16名训练患者完全不重叠，reserved overlap=0；
- 每患者固定hash抽10条，抽样不读取GT；
- 四路main请求只包含proposition/reference，模式参数逐条核验；
- G/M训练患者与评价患者完全隔离；
- Gate A每个评价患者的模型都排除该患者；
- 22个Qwen候选可由fresh N-S分数逐条重算；
- 1030个attempt与冻结job和receipt一一绑定，全部HTTP200，无成功答案重跑；
- 累计费用低于任务cap。

有一个必须保留的执行顺序限制：GT_connection.json在主API全部完成之前已物化。虽然样本抽取、API payload、G/M参数、Gate模型和Qwen候选均不依赖052 GT，且没有052 GT进入模型或参数，但本轮不满足最严格的“预测全部封存后才解盲”流程。因此052应定位为 **development内部探索性同场验证**，而不是新的reserved/external confirmation。

另有两项非科学实现修正：
1. 当前环境历史SciPy L-BFGS-B进程级退出，API前改用确定性纯NumPy求解同一G/M凸NLL+正则目标，并做有限差分梯度/单调下降检查；
2. main_freeze漏写repeat具体ID，分析时从冻结main_jobs中的_repeat条件确定性恢复12个ID。两项均不改变方法、样本、预测或参数定义。

## 11. 研究判断

052把第一梯队大幅收缩：

1. **保留：T-S + 固定U2。** 它是唯一从051跨到新24名患者仍保留性能/风险正信号的路线。总体PA大致持平U2，但false-S明显更少、MCC和NS/NA表现更健康；相对患者外Gate A的MCC配对患者区间为正。
2. **尤其值得重视：human-written claims。** T-S+U2在human组点估计同时超过U2、Gate A和原VeriFact，并显著减少false-S；这与原VeriFact在人写BHC上性能下降的已知难点直接相关。
3. **停止：N-V/T-V作为overall accuracy替代。** 低false-S仍真实，但051的accuracy优势未迁移。
4. **停止：N-V→thinking cascade。** 052明确出现净harm。
5. **停止当前051-trained G/M迁移。** 平衡训练分布上的NLL校准没有提高052分类性能；固定λ2反而更稳。

下一步若继续，最值得做的不是再开新机制，而是围绕 **T-S+U2** 做更严格的确认：解决结构无效/长度失败，冻结一个明确fallback，并在真正未参与开发的新患者/外部材料上比较U2、Gate A、原VeriFact和T-S+U2。不能再用已消费reserved40调这个工作点。
