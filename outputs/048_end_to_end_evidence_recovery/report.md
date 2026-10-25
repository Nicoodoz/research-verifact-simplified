> 阅读镜像：已省略1行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# 048：End-to-End GT-Blind Evidence Recovery

## 核心结论

048直接验证了039→043最关键但此前缺失的一环：**不事先挑选“full-EHR搜索成功”的病例时，GT-blind自动查证恢复是否仍能形成可泛化的净收益。**

本轮答案是否定的：K与G都出现真实的正向个例，但都没有达到预注册的screen晋级门槛，因此按协议停止，不执行已事前冻结的29条患者隔离confirmation。

| 条件 | raw正确 | raw rescue/harm/net | U2正确 | U2 rescue/harm/net | raw false-S变化 | 晋级 |
|---|---:|---:|---:|---:|---:|---|
| B 原E0 | 2/16 | baseline | 9/16 | baseline | 0 | baseline |
| K D48内查证恢复 | 3/16 | 1 / 0 / +1 | 11/16 | 3 / 1 / +2 | 0 | 否 |
| G 完整EHR查证恢复 | 3/16 | 1 / 0 / +1 | 10/16 | 2 / 1 / +1 | 0 | 否 |

事前门槛要求raw净正确至少+2、至少2个raw rescue且跨至少2名患者、raw harm最多1，同时U2不得净下降且U2 harm最多1。K/G的raw rescue都只有1条且集中在同一患者，所以不扩大。

## 1. 为什么048和043不同

043的55条固定样本已经满足GT=Supported、U2正确救回，而且039已自动找到C48外严格支持证据。因此043证明的是：**当目标证据已经成功定位时，把它交给原DeepSeek确实有下游utility**；严格配对得到13条raw non-S→S、0条反向。

048不使用这些reserved post-hoc成功病例开发方法。它从development中只根据系统自身可见的冲突触发：
- 原DeepSeek raw verdict不是Supported；
- 固定λ=2后U2=Supported。

这类冲突既可能是真正被U2救回的S，也可能是被U2错误推成S的NS/NA。048不在运行前知道哪一种，因此可以检验完整自动恢复流程是否会同时帮助正确翻转、抑制错误翻转，还是制造新的harm。

044 evaluation中该触发母体共76条、8名患者；患者固定hash分成4名screen和4名confirmation。Screen每名患者固定hash取4条，共16条；冻结后查看GT为13 S、2 NS、1 NA。另4名患者全部29条触发病例在任何048结果出现前已冻结，但因screen失败没有调用。

## 2. K和G实际做了什么

两条路线共享同一套claim-only query plan。Qwen只看到claim，生成material requirements和最多4条保守查询，不看GT、U2、旧reason或旧预测。

K的候选范围只限于原031 C48候选中未进入E0的passage。

G使用同患者、同目标住院的031 eligible corpus，复用冻结embedding：原claim做完整dense与BM25排序，扩展query做BM25排序，多路RRF后排除E0并固定取top32。这里采用的是039真实冻结实现的32，而不是旧039 protocol文字中的80。

随后K/G都用同一套Qwen逐要求证据审计。审计可以判Supported、Not Supported、Not Addressed或Uncertain，必须给逐字引用。程序不会把Qwen的audit label、summary或reason交给DeepSeek，只提取逐条quote校验通过的外部passage ID，最多12个去重原始passage追加到完整E0，再调用原DeepSeek scoring Judge。

因此最终DeepSeek看到的仍然只有claim和原始EHR文本。若没有合法外部引用，该条件直接复用本轮同期B。

## 3. 自动链路确实找到了证据，但没有形成稳定raw净收益

16条中：
- K有9条最终reference发生变化，共追加11个经逐条quote校验通过的外部passage；最终DeepSeek在7条中显式引用了新增编号。
- G有8条reference发生变化，共追加12个外部passage；最终DeepSeek同样在7条中显式引用新增编号。

Qwen审计label：
- K：Supported 5、Not Supported 11；
- G：Supported 6、Not Supported 10。

所以这条链路不是“只寻找支持U2的证据”。它确实会找到反证/不足证据，并将这些原始passage交给DeepSeek。

但最终raw verdict层，K与G都只救回1条、0 harm，净+1；而且两者救回的是同一条claim、同一名患者。**K与G的16条raw最终标签完全一致。**

这意味着在本批screen中，把搜索范围从D48扩大到完整eligible EHR，没有转化为额外的raw分类收益。当前不能据此声称full-EHR search优于已有候选池。

### 一个真实的端到端正例

唯一raw rescue是：


医生GT=Supported。同期B的DeepSeek为Not Supported；K和G的审计都自动找到并引用了1个外部原始passage，最终DeepSeek在新reference上直接改为Supported，并在checks中引用新增证据。

这说明039→043机制不是只在reserved事后成功样本里存在：在新的development患者材料上，GT-blind自动查证链也能产生真实的raw Judge rescue。

但它只有1条、1名患者，因此不能成为路线级成功证据。

## 4. 对U2的影响比raw更复杂：既有修复，也有新harm

同期B的U2只有9/16正确；K为11/16，G为10/16。

K相对B：
- 3 rescue / 1 harm，净+2；
- false-S数量不变。

G相对B：
- 2 rescue / 1 harm，净+1；
- false-S数量不变。

其中有几类不同机制：

1. **修复错误U2翻转。**  
   “right knee I+D with patella tendon repair”医生GT=Not Supported。B raw本来就是正确NS，但B的λ2又把它推成错误S；K/G加入审计引用的反证后，raw仍NS，而U2也回到NS。也就是说，额外证据可以改变score结构，从而修复后处理造成的false-S。

2. **raw不变但让U2跨过正确边界。**  
   “required transfer to the MICU service on 9-16”GT=Supported。B raw与U2都为NS；K/G加入支持证据后raw仍NS，但U2变S，形成正确救回。

3. **证据也可能把正确U2推错。**  
   “subsequently suffered ARDS with progressive worsening...”GT=Not Supported。B raw/U2都是正确NS；K/G新增证据后raw仍NS，但Supported score移动使U2变成错误S。

所以“找到相关且可引用的证据”不保证λ后处理更安全。证据改变会重新塑造label_scores，而固定λ是在旧输入分布上开发的。

## 5. 048再次显示：raw verdict比λ依赖的score边界稳定

Supported score均值：
- B：14.38；
- K：21.56；
- G：20.31。

说明查证后的目标原文整体上确实改变了DeepSeek的Supported评分；这不是“证据完全没被模型看到”。

但是分数层比raw verdict明显更容易跨运行漂移：

- 这16条按044历史记录全部满足U2=S；本轮同期B有**6/16**的U2与历史不同，而raw verdict历史→本轮为**0/16变化**。
- 6条固定B同输入repeat：raw **0/6变化**，U2 **2/6变化**。
- 6条固定G evidence pack repeat：raw **0/6变化**，U2 **1/6变化**。

其中“coagulation studies slightly elevated”一例，K看似把U2从NS救到S，但本轮B repeat在完全相同E0下自己也从NS变成S，而且K最终reason没有显式引用新增编号。因此这类score边界变化不能稳健归因于证据恢复。

这也是为什么048预注册把raw verdict设为主要机制终点，并要求raw出现跨患者的净改善后才扩大，而没有因为K的U2净+2就事后启动confirmation。

## 6. 完整EHR G没有超过D48内K

在这16条上：
- K改变9条reference，G改变8条；
- K最终追加11个external passage，G追加12个；
- 两者最终DeepSeek显式引用新增编号都是7条；
- K与G的raw标签16/16完全相同；
- U2只有1条不同。

这说明048没有复现“只有扩大到完整EHR范围才能获得额外下游收益”的信号。至少在本screen中，真正能影响Judge的材料大多已经能从D48范围内被查证链找到，扩大搜索范围没有增加raw rescue。
这并不否定039中的B类missing-evidence机制。039的病例是reserved后的post-hoc机制集；048回答的是：未按搜索成功筛选的冲突触发器上，扩大搜索范围是否能形成额外净收益。本轮没有。

引用校验：G的16份audit均为整体引用有效；K为11/16。最终证据包只使用逐条通过quote核验的external passage，因此K审计中的其他引用问题没有进入最终Judge输入。

## 7. 成本与执行

收费API共90次，90/90 HTTP200：
- screen stage1：16次同期B、16次claim-only query、6次B repeat，共38次，约¥0.300285；
- screen stage2：K/G evidence audit各16次，共32次，约¥1.098546；
- screen stage3：去重后的K/G final Judge与6次G repeat共20次，约¥0.258531。

总usage估算约 **¥1.657362 / ¥10 screen cap**；其中Qwen约¥1.126113，DeepSeek约¥0.531249。没有因为费用低就自动运行29条confirmation。

第一次零API构建G搜索索引时发现031的vectors.npy只包含部分已有向量；该尝试在任何新API前失败。随后严格按031原pipeline逻辑，从031已保存的embedding HTTP200 receipts重建其余冻结向量，再完成本地索引；没有发送新的embedding请求，也没有修改031 artifact。

## 8. 完整性核验

执行者离线verification共222项检查PASS，主要包括：
- screen与confirmation患者完全隔离，全部属于development，reserved overlap=0；
- 所有screen/confirmation病例都满足冻结的系统可观测触发器；
- K candidate严格来自各claim的D48 extras；
- G每条最多32个候选、排除E0，并且全部属于同患者corpus；
- query请求只含proposition，audit请求只含proposition/C48/additional EHR，final Judge只含proposition/reference；
- 每个真正追加的passage都能逐字回查到031 frozen corpus；
- 90个请求均有唯一HTTP200回执，累计费用低于screen cap；
- 无任何confirmation API调用。

执行者verification PASS不等于独立审计PASS；当前仍待独立复核。

## 9. 如何解释048

048并没有推翻043。043证明“自动审计已经成功定位到的目标证据”具有真实Judge utility；048进一步说明：**把这条查证链直接用于所有可观测raw-vs-U2冲突，并不能稳定把条件性headroom转化成跨患者raw净收益。**

最重要的收缩是：

1. **候选池宽度不是当前最明显的瓶颈。**  
   K与G raw结果完全相同，full-EHR范围没有超过D48内查证。

2. **逐要求查证比通用相关性selector更有机制价值，但成功仍稀疏。**  
   16条中确实出现1个干净raw rescue，并能找到支持和反证两类材料；但只有1名患者，达不到扩大标准。

3. **证据改善与固定λ并非天然兼容。**  
   新证据明显移动Supported scores，既能修复错误U2，也能制造新的U2 harm。旧输入上开发的λ=2不应被假定在证据分布改变后仍保持相同风险工作点。

4. **当前最稳定的信号仍是raw verdict。**  
   raw跨历史与同期repeat都很稳定；U2依赖的label_scores存在明显运行漂移。后续若研究证据恢复，应继续把raw改变和最终postprocess改变分开报告。

## 10. 结论边界

048没有重算或改变036的整体PA/MCC，也没有形成新的默认系统。Screen是系统冲突触发子集，不是自然benchmark，因此2/16、3/16等比例不能写成总体准确率。

当前可以声称：
> GT-blind逐要求证据恢复能够在少量新development病例中找到真正改变原Judge或U2边界的原始EHR证据，但在未预筛搜索成功的冲突触发器上，D48内恢复和full-EHR恢复都未形成达到预设门槛的跨患者raw净收益；扩大搜索范围也未超过D48候选内恢复。

当前不能声称：
- 已经自动复现043的13/0效果；
- full-EHR搜索优于D48；
- K的U2净+2代表稳定系统性能提升；
- 证据恢复已解决label-reason矛盾；
- 048提供新的整体PA/MCC提升。

因此按协议停止confirmation，不事后放宽门槛或组合K/G继续搜索。若后续继续，这批结果更支持研究“哪些已查证关系值得改变Judge/score，以及证据改变后决策边界如何重新校准”，而不是继续单纯扩大检索范围。
