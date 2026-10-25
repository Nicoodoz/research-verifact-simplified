> 阅读镜像：已省略310行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

## 2. 阅读两份完整 BHC

这一节只翻译“待核验文本说了什么”，不提前把其中内容判断为正确。

### 2.1 Human-written BHC：完整英文原文

来源：`propositions.csv.gz`，筛选 `subject_id=5954, author_type=human`，读取去重后的 `brief_hospital_course`。

```text
ablation and pacemaker placement, dCHF, hypertension transferred
for pacemaker revision.
.
# pacemaker malfunction:  The patient has a history of atrial
fibrillation s/p AV ablation and is pacemaker dependent.  His
pacemaker was failing to capture when he raised his left arm.
He went into a junctional rhythm on the night of his admission
when his pacemaker mode was changed to DDI with rate of 40.  He
was hemodynamically stable at this rate, and the following day
the patient underwent explant of previous pacemaker and inplant
of a new right sided pacemaker with a single ventricular lead.
The patient's heartrate increased to 70 paced rythm.

#Atrial fibrillation: The patient's coumadin was held and 2mg of
vitamin K was given in anticipation of his pacemaker procedure.
He was restarted on his home dose of coumadin to be followed by

# CORONARIES:  The patient has no history of CAD.
```

**中文翻译**

[姓名已脱敏]先生，56 岁男性，有心房颤动病史，曾接受房室结消融和起搏器植入，并患有舒张性充血性心力衰竭、高血压，因起搏器修正手术转院。

**起搏器故障：**患者有心房颤动病史，曾接受房室结消融，并依赖起搏器。当他抬起左臂时，起搏器无法有效夺获心肌。入院当晚，起搏器模式改为 DDI、频率设为每分钟 40 次时，他出现交界性心律。在这一心率下，患者的血流动力学保持稳定。次日，患者取出了原有起搏器，并在右侧植入了一台带单根心室电极导线的新起搏器。患者心率升至每分钟 70 次，呈起搏心律。

**心房颤动：**为准备起搏器手术，暂停了患者的华法林，并给予 2 mg 维生素 K。随后恢复了他在家服用的华法林剂量，出院后由其初级保健医生[姓名已脱敏]随访。

**冠状动脉情况：**患者没有冠心病史。

原文的 `inplant`、`rythm` 等拼写及独立句点没有在英文中修正。译文按上下文表达其含义。

### 2.2 LLM-written BHC：完整英文原文

来源：同表，筛选 `subject_id=5954, author_type=llm`。

```text
The patient was admitted to the hospital after experiencing 5-second pauses due to pacemaker malfunction. Initial evaluation revealed intermittent failure to capture and oversensing, leading to pacing inhibition, and the pacemaker was reprogrammed. A chest X-ray suggested possible lead migration, and the patient was planned for overnight observation, reversal of anticoagulation, and lead revision surgery the following day. The patient underwent successful lead revision in the electrophysiology lab and was found to have a kinked pacer wire causing the malfunction. Post-procedure chest X-ray showed the new pacemaker lead in the correct position in the right ventricle. The patient was stabilized and monitored on telemetry throughout his hospital stay, with no significant complications or changes in his cardiac rhythm.
```

**中文翻译**

患者因起搏器故障出现持续 5 秒的心搏停顿后入院。初步评估发现起搏器间歇性夺获失败及过度感知，导致起搏被抑制，随后重新设置了起搏器。

胸部 X 线提示电极导线可能移位，计划让患者留院观察一夜、逆转抗凝作用，并于次日进行电极导线修正手术。患者在心脏电生理室成功接受了电极导线修正手术，并发现起搏导线扭折是引起故障的原因。

术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。患者在整个住院期间病情得到稳定，并接受遥测心电监护，未出现明显并发症或心律变化。

**阅读解释：**两份 BHC 描述的是同次住院，但选取的信息不同。human BHC 写了既往病史、药物恢复及随访；LLM BHC 写了 5 秒停顿、过度感知和“整个住院期间”的概括。是否得到支持，需要分别连接医生标签、检查参考 EHR，不能仅凭两份 BHC 是否互相一致来判断。

## 3. 看一个文本块怎样得到两种 proposition

### 3.1 真正的 parent_text_chunk

本例 human BHC 有 3 个不同的 `parent_text_chunk`，LLM BHC 有 2 个。本文按其在 BHC 中的位置，分别称为 H1—H3、L1—L2。

下面是 **LLM BHC 的第二个文本块 L2**，直接取自 `parent_text_chunk`：

```text
Post-procedure chest X-ray showed the new pacemaker lead in the correct position in the right ventricle. The patient was stabilized and monitored on telemetry throughout his hospital stay, with no significant complications or changes in his cardiac rhythm.
```

**中文翻译：**术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。患者在整个住院期间病情得到稳定，并接受遥测心电监护，未出现明显并发症或心律变化。

这个字段保存的是一段来源文本。它不是医生标签，也不是从 EHR 检索出来的证据。

### 3.2 在 sentence 视图中，它对应两行

| 编号 | 中文翻译 | 最终标签 |
| --- | --- | --- |
| L-S05 | 术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。 | `Supported` |
| L-S06 | 患者在整个住院期间病情得到稳定，并接受遥测心电监护，未出现明显并发症或心律变化。 | `Not Supported` |

### 3.3 在 atomic claim 视图中，它对应四行

| 编号 | 中文翻译 | 最终标签 |
| --- | --- | --- |
| L-C10 | 术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。 | `Supported` |
| L-C11 | 患者在整个住院期间病情得到稳定，并接受遥测心电监护。 | `Not Supported` |
| L-C12 | 患者在整个住院期间没有出现明显并发症。 | `Not Addressed` |
| L-C13 | 患者在整个住院期间没有心律变化。 | `Not Supported` |

**阅读解释：**

- 同一来源块中的两个 sentence 和四个 claim 是两套核验对象；不能把它们当作六个互不相关的事件。
- L-S06 包含多个方面，claim 视图把它们分别表达为 L-C11、L-C12、L-C13。它们得到的医生标签也不同。
- 此处“L-S06 对应这三条 claim”是根据原文内容作出的阅读对应。发布表没有直接提供 `claim → sentence_id` 外键；数据中可直接核对的是相同 BHC、相同 `parent_text_chunk`。
- 不要把整句的医生标签复制给所有 claim，也不要用某个固定合并规则反推整句标签。这里展示的是各行已经独立获得的标注。

### 3.4 “Atomic claim”不保证每行只剩一个最小动作

真实的 L-C02 是：

```text
Initial evaluation revealed intermittent failure to capture and oversensing, leading to pacing inhibition.
```

中文：初步评估发现起搏器间歇性夺获失败及过度感知，导致起搏被抑制。

其中仍然包含“夺获失败”“过度感知”“导致起搏被抑制”等信息。H-C19 也同时包含恢复用药和出院随访。**`proposition_type=claim` 是作者切分结果的类型标记，不是对每条文本都已达到绝对不可再分的保证。**

本例还有内容重复：H-C02、H-C08、H-C16 都涉及房颤，但措辞或来源块不同，并有各自的 ID。

## 4. 医生标签和有效性标签怎样读

### 4.1 本文的标签简写

| 简写 | 数据中的原值 | 阅读时的含义 |
| --- | --- | --- |
| S | `Supported` | 命题得到参考 EHR 的支持 |
| NS | `Not Supported` | EHR 涉及相关内容，但未充分支持命题，或存在矛盾 |
| NA | `Not Addressed` | 参考 EHR 未涉及该命题所述内容 |

这三类都针对数据集提供的参考 EHR；`Not Addressed` 不等于事情在现实中一定没发生，`Not Supported` 也不必然意味着整句话每个部分都是错误的。

第 7 节中的 `NS / NA / NS → NS` 表示：按 `verdict1`、`verdict2`、`verdict3` 的顺序，三名医生分别给出 NS、NA、NS，最终 `human_gt=NS`。不同命题的三名医生不一定相同。

### 4.2 展开一条真实标注记录：L-C13

待核验命题：

```text
The patient had no changes in his cardiac rhythm throughout his hospital stay.
```

中文：患者在整个住院期间没有心律变化。

| 字段 | 原始值 |
| --- | --- |
| `rater1 / verdict1` | `S / Not Supported` |
| `rater2 / verdict2` | `H / Not Addressed` |
| `rater3 / verdict3` | `N / Not Supported` |
| `round1_num_raters_agree` | `2` |
| `round1_majority_vote` | `Not Supported` |
| `human_gt` | `Not Supported` |
| `uncertain_flag1 / 2 / 3` | 均为 `False` |
| `comment1 / 2 / 3` | 均为空 |
| 后续轮次及裁决字段 | 本行为空 |

此表中 `rater1=S` 的 **S 是医生代号**，不要与本文用于 Supported 的简写 S 混淆。

本病例全部 50 行都有第一轮多数票：35 行三人一致，15 行为两人一致，`human_gt` 均等于第一轮多数票。因此，这个病例没有展示“三人各投一类后再裁决”的情况。

本病例的第一轮评论均为空。后文对证据的解释不能称为“医生写下的理由”。

### 4.3 相近内容也可能出现不同的最终标签

| 对象 | 中文内容 | 三人投票 | human_gt |
| --- | --- | --- | --- |
| H-S10，sentence | 恢复原华法林剂量，出院后由具名的初级保健医生随访 | NA / NS / NS | NS |
| H-C19，claim | 恢复原华法林剂量，出院后由初级保健医生随访 | NA / NS / NA | NA |

两条命题内容接近，但独立标注后的多数票不同。这里不能据此断定是哪位医生错误，也不能断定“删去姓名”导致了标签变化；它首先说明 **标签要按 proposition_id 连接，不要按大致相同的文本含义替换**。

### 4.4 有效性是另外一条判断轴

本例存在两个很直观的真实异常：

| 编号 | 原始 text 的 Python 表示 | human_gt | invalid | 其他最终有效性字段 |
| --- | --- | --- | --- | --- |
| H-S01 | `'Mr. '` | `Not Addressed` | `True` | `incomplete=True, vague=True` |
| H-S03 | `'.\n'` | `Not Addressed` | `True` | `incomplete=True` |

它们来自 human BHC 开头的真实切分结果，不是为了举例临时构造的。

与之对照，L-C12“整个住院期间没有明显并发症”的 `human_gt` 也是 `Not Addressed`，但 `invalid=False`。它能表达一个可核验的陈述，只是医生没有给出 Supported 标签。

**阅读解释：**“是不是有效命题”和“有没有 EHR 支持”是不同问题。无效命题仍可能保留医生标签；不能把 `invalid=True` 当作另一个事实核验类别，也不能看到 NA 就自动认定文本无效。本节使用的是最终有效性字段，不是 `*_draft`。

## 5. 从命题回到参考 EHR

本节引用 `reference_ehr/ehr_noteevents.csv.gz` 中 `SUBJECT_ID=5954` 的记录。每条摘录都有 note 的 `ROW_ID`。

**这些证据片段由本次阅读选取，用来理解原始医生标签；数据没有提供“该医生标签对应这几个证据片段”的金标准映射。**

### 5.1 Supported：导线位于右心室内的正确位置

对象：L-C10，医生三人均标为 `Supported`。

证据来自：

- `ROW_ID=1122851`
- `CATEGORY=Radiology`，`DESCRIPTION=CHEST (PA & LAT)`


```text
A new pacemaker lead is in appropriate position in the
 right ventricle.
```

**中文：**新的起搏器电极导线在右心室内的位置合适。

**阅读解释：**这与 L-C10 的关键内容“新导线—右心室—位置正确”直接对应。

### 5.2 Not Supported：整个住院期间都没有心律变化

对象：L-C13，医生标签为 `Not Supported`，第一轮两人 NS、一人 NA。


```text
On admission to CCU,  HR 70
s Afib.  Pacer interrogated by EP &
   pacemaker rate lowered to 40. Presently in JR.
```

**中文：**入心脏监护病房时，心率为每分钟 70 多次，呈房颤。电生理团队检查了起搏器，并将起搏频率调低至每分钟 40 次。目前呈交界性心律。


```text
Ventricular paced rhythm.  Atrial mechanism is uncertain.  Since the previous
```


**阅读解释：**参考记录中同时存在房颤、交界性心律、心室起搏心律等描述。“与前次心电图相比可能没有显著变化”只限定在特定检查比较中，不能直接扩展成“整个住院期间没有心律变化”。这些摘录帮助理解 NS 标签，但不能替代对全部参考记录的临床裁决。

### 5.3 Not Addressed：整个住院期间没有明显并发症

对象：L-C12，医生标签为 `Not Addressed`，第一轮两人 NA、一人 S，`invalid=False`。

同一条护理记录 `ROW_ID=401900` 中有：

```text
Hemodynamically stable throughout night.
```

**中文：**整夜血流动力学稳定。

**阅读解释：**“某一夜血流动力学稳定”与“整个住院期间没有明显并发症”不是相同范围的陈述。不能只找到一个局部稳定的片段，就认为整个住院经过的概括已得到支持。

这里的 NA 是直接读取的医生最终标签；展示一段局部记录本身无法证明“所有 EHR 都没有相关信息”。医生对此也并非全体一致。

### 5.4 “准备做”“做过”“一直如此”需要分开读

L-C06 的原文是 `The patient was planned for reversal of anticoagulation.`，译文应保留“计划”，不能改成“已经完成”。

参考记录 `ROW_ID=401900` 还写道：

```text
Cont. to hold coumadin for EP procedure.
```

**中文：**为电生理操作继续暂停华法林。

这句话能帮助理解“为操作暂停华法林”，但它本身不能证明 H-C19 所说的“之后恢复原剂量并安排出院随访”。

同样，BHC 中的 `throughout his hospital stay`（整个住院期间）、`the following day`（次日）、`possible`（可能）都是命题含义的一部分，翻译、检索和判断时都需要保留。

## 6. 再看作者发布的 AI 判断

本节读取的是已有的 `verdicts.parquet` 和 `reference_payloads.parquet`，没有重新调用模型生成结果。

### 6.1 固定一个真实配置

来自 `rater_configurations.csv`：

| 字段 | 原始值 | 中文含义 |
| --- | --- | --- |
| `rater_alias` | `v1.1.0-rater-121` | 模型与检索配置的联合标识 |
| `model` | `R1-70B` | 发布表中的 Judge 模型名称 |
| `fact_type` | `sentence` | EHR 证据侧采用 sentence facts |
| `retrieval_method` | `rerank` | 使用重排序的检索配置 |
| `top_n` | `100` | Top-N 参数值 |
| `reference_format` | `absolute_time` | 参考文本带绝对日期、时间 |
| `reference_only_admission` | `True` | 仅本次住院的检索设置 |
| `deduplicate_text` | `True` | 开启文本去重 |

**`fact_type=sentence` 描述证据 EHR 的粒度，不意味着待核验 proposition 必须也是 sentence。**下面的 L-C13 就是用 sentence facts 核验一个 claim proposition。

### 6.3 reference_payloads 里实际长什么样

以 L-C13 为例，`verdicts.parquet` 中记录的 `reference_id` 为：

`fa1914b787962220e2ba597bc77c25ee03f5f34a83db75a1bed78d39e7c9a649`

通过该值连接 `reference_payloads.parquet`，得到真实送给模型的参考文本。该 payload 有 **100 个编号条目**，开头如下：

```text
Electronic Health Record Context
Ordered by Time (Earliest to Latest):
```

**中文：**

- 电子病历参考上下文，按从早到晚的顺序排列。

其中与心律有关的第 74、98 条如下。只展示这两个条目，其他内容没有在本文中展开：

```text
```
```text
```

**中文：**


这里的“74”“98”只是当前 payload 内的编号，**不是 NOTEEVENTS 的 `ROW_ID`**。第 98 条可以按内容及日期回查到第 5 节的 ECG 记录；第 74 条的相同文字出现在 `ROW_ID=401915` 和 `401916` 两条 note 中。不能假定上下文中的每个片段都能唯一反查到一条 note。

再看 L-C10 的真实上下文：虽然同样设置 `top_n=100`，实际只有 **99 个编号条目**。其中第 89 条是：

```text
 right ventricle.
```


因此，`top_n` 是配置参数，不能不读 payload 就假定实际总有相同数量的证据。这里仅报告实际数量，不据此判断少一条的具体原因。

### 6.4 用 ID 回查这五条模型结果

所有行的 `rater_alias` 都是 `v1.1.0-rater-121`；完整 `proposition_id` 在第 9 节。

| 本文编号 | reference_id |
| --- | --- |

| L-C10 | `7dab5c85d8217d308fef8c6d3932a3166d500891f58806d3780a303d6c2891b9` |
| L-S06 | `3b047aa0ed706d4cca8c2b39652b0bbe5962b3401ba6b5db820fcfe83e2f2308` |
| L-C11 | `2ae46c7f9c8fe2ed969e289fa07d2bf1d84fd8138dcbffa682b3ed598898911a` |
| L-C12 | `7411fd7704b926f9e9addaa8dae9524b44ae35f4bff6dbc531cf3cfa7f84c157` |
| L-C13 | `fa1914b787962220e2ba597bc77c25ee03f5f34a83db75a1bed78d39e7c9a649` |

`reference_id` 对应精确上下文内容；本文引用的 L-C10、L-C13、L-S06 三个 payload 已重新计算 UTF-8 文本的 SHA-256，并确认与各自 ID 一致。

## 8. 这位患者的全部参考 EHR 目录

这是 `ehr_noteevents.csv.gz` 中该患者的全部 11 行，而不是只列出上文用到的记录。类别分布为：医生记录 4 条、护理记录 3 条、放射记录 2 条、心电图报告 2 条。没有出院小结，也不包含 human BHC 来源记录 `ROW_ID=21797`。

本病例只含本次住院的参考记录，不能据此推断其他患者也没有历史住院记录。

| ROW_ID | CHARTDATE / CHARTTIME | 原始 CATEGORY / DESCRIPTION | 中文说明 |
| --- | --- | --- | --- |


表格保留发布文件中的行次序；没有具体时刻的 ECG 不据此判断当天先后。以上时间是 `CHARTTIME` 或 `CHARTDATE`，不是 `STORETIME`。

`401915` 与 `401916` 的 `TEXT` 在本地文件中完全相同，但 `ROW_ID` 和 `STORETIME` 不同，本文均予以保留。这也说明“原始 note 行”和“不同的文本内容”不是同一统计口径。

## 9. 全部命题 ID 与来源块索引

下表用于回到原始 CSV 定位。H1—H3、L1—L2 是本文给不同 `parent_text_chunk` 添加的简称。

| 本文编号 | 来源块 | proposition_id |
| --- | --- | --- |


## 10. 读完后做四个小练习

1. 在 L-S03 和 L-C04—L-C07 中，指出哪些词表达“可能”，哪些词表达“计划”，并解释为什么不能把它们翻译成已经完成的事实。
2. 不看模型输出，先读 L-S06、L-C11—L-C13 的医生标签，说明一句话中为什么会有不同层面的核验问题。
3. 对比 H-S01 与 L-C12：它们都是 NA，为什么只有前者 `invalid=True`？
4. 从 L-C13 开始，依次说出查原文、医生标签、AI 结果、AI 输入证据时各自用的键。

回答第 4 题需要的路径：

```text
L-C13
  → 本文第 9 节取 proposition_id
  → propositions.csv.gz 查 text / brief_hospital_course / parent_text_chunk
  → human_verdicts.csv.gz 查 human_gt 与三名医生的票
  → verdicts.parquet 以 proposition_id + rater_alias 查一次 AI 判断
  → 取该行 reference_id
  → reference_payloads.parquet 查该次判断真正收到的 reference
```

进一步查看证据原始 note 时，使用患者 `SUBJECT_ID`、日期、类别、正文内容等回查 `ehr_noteevents.csv.gz`。不要把模型参考条目的局部编号当作 note ID，也不要把本次阅读挑出的证据当作医生发布的证据金标准。

## 11. 数据来源与本次核对范围

本导读只使用仓库内的这些文件：

- [官方数据字典](../data/00_raw/verifact-bhc/1.1.0/README.md)。
- [propositions.csv.gz](../data/00_raw/verifact-bhc/1.1.0/propositions/propositions.csv.gz)：BHC、来源块、命题、患者及住院标识。
- [human_verdicts.csv.gz](../data/00_raw/verifact-bhc/1.1.0/propositions/human_verdicts.csv.gz)：医生个体投票和最终标签。
- [proposition_validity.csv.gz](../data/00_raw/verifact-bhc/1.1.0/propositions/proposition_validity.csv.gz)：最终有效性字段。
- [admissions.csv.gz](../data/00_raw/verifact-bhc/1.1.0/reference_ehr/admissions.csv.gz)：目标住院信息。
- [ehr_noteevents.csv.gz](../data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz)：参考 note 与原始正文。
- [rater_configurations.csv](../data/00_raw/verifact-bhc/1.1.0/verifact/rater_configurations.csv)：本节使用的模型及检索配置。
- [verdicts.parquet](../data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet)：作者发布的 AI 判断与理由。
- [reference_payloads.parquet](../data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet)：真实模型输入上下文。

本次按患者 ID 筛选并通过命题 ID 连接，不按相同文本猜测标签。完成核对的内容包括：两份 BHC 的唯一性、50 条命题及中英对照的完整性、所有标签与原始行的一致性、引用 EHR 片段确实存在于注明的 note、选定模型结果及 reference_id 的对应关系。

中文翻译和阅读解释服务于理解这一个真实样本。原始事实标签保持原值；本导读没有开展新的模型实验，也没有改写你的《数据集笔记》和《论文笔记》。
