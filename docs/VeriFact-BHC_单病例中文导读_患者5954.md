# VeriFact-BHC 单病例中文导读：患者 5954

这份文档从本地 **VeriFact-BHC v1.1.0** 提取真实记录，带你读通：

**完整 BHC → 来源文本块 → sentence / atomic claim → 医生标签 → 参考 EHR → 作者发布的模型结果。**

本病例的两份 BHC、全部 **50 条 proposition** 均保留英文，并提供中文翻译。EHR 和模型上下文只摘录与讲解有关的片段，明确注明出处。

- 数据目录：`data/00_raw/verifact-bhc/1.1.0/`
- 整理日期：2026-09-12。
- 选例理由：两份 BHC 较短，同时包含三类医生标签、有效性异常和标注分歧，便于首次阅读。这是有目的选择的教学病例，不代表整个数据集的分布。
- 英文内容、ID 和标签来自数据文件；中文翻译与标有“阅读解释”的内容由本次整理添加。翻译不是新的医学标注，也不是原实验的模型输入。
- `[**...**]` 是原数据中的脱敏占位符，英文原样保留；中文将人名统一写成“[姓名已脱敏]”。日期按数据原值展示，不据此还原现实身份或时间。
- 英文代码块保留原始措辞、拼写及换行。命题表格为便于阅读，将换行及连续空白合并为空格，不改词语。

建议先读第 1—5 节，再读第 6 节的模型对照。第 7 节列出全部命题，第 8—9 节用于回查。

## 1. 先认识这个病例和文件关系

### 1.1 患者、住院、文档、命题是不同层级

| 层级 | 本病例中的真实值 | 含义 |
| --- | --- | --- |
| 患者 | `subject_id = 5954` | 关联这位患者的两份 BHC、命题和参考 EHR |
| 目标住院 | `hadm_id = 183959` | 本次 BHC 描述的住院 |
| 入院 | `2112-02-29 18:24:00` | 来自 admissions |
| 出院 | `2112-03-02 15:20:00` | 来自 admissions |
| 入院诊断字段 | `COMPLETE HEART BLOCK;MALFUNCTIONING PACEMAKER` | 完全性心脏传导阻滞；起搏器故障 |
| human BHC | 1 份，1,065 个字符 | 这里指 `brief_hospital_course` 字段，不是整份出院小结 |
| LLM BHC | 1 份，826 个字符 | 同一患者、同次住院的模型生成 BHC |
| 原始参考 EHR | 11 条 note | 本病例全部属于住院 `183959`，没有其他住院的 note |
| 待核验命题 | 50 条 | 两份 BHC、两种切分粒度产生的全部行 |

英文 BHC 字符数按 Python `len` 计算，包含空格和换行。以上均为这一个病例的统计。

`human-written` 表示谁写了待核验 BHC；`human_gt` 表示医生核验后的标签。**医生写的 BHC 同样是待核验文本，不能直接充当另一份 BHC 的正确答案。**

### 1.2 四组命题的数量

| BHC 来源 | proposition_type | 数量 | Supported | Not Supported | Not Addressed | invalid=True |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| human | sentence | 11 | 7 | 2 | 2 | 2 |
| human | claim | 20 | 18 | 1 | 1 | 0 |
| llm | sentence | 6 | 5 | 1 | 0 | 0 |
| llm | claim | 13 | 10 | 2 | 1 | 0 |
| 合计 | — | 50 | 40 | 6 | 4 | 2 |

这 50 行不是 50 个互相独立的临床事件。例如，同一内容会同时出现在 sentence 和 claim 中，也可能在 BHC 内重复出现。

### 1.3 实际通过哪些键连接

```text
propositions.csv.gz
  ├─ subject_id = 5954 ─────────→ ehr_noteevents.csv.gz 的 SUBJECT_ID
  ├─ hadm_id = 183959 ──────────→ admissions.csv.gz 的 HADM_ID
  └─ proposition_id
       ├────────────────────────→ human_verdicts.csv.gz
       ├────────────────────────→ proposition_validity.csv.gz
       └────────────────────────→ verdicts.parquet
                                    ├─ rater_alias → rater_configurations.csv
                                    └─ reference_id → reference_payloads.parquet
```

本例 human 命题的 `row_id` 是 `21797.0`，对应来源出院记录；LLM 命题的 `row_id` 为空。不要把这个字段当作命题序号或参考 EHR 的证据编号。参考 note 有自己的 `ROW_ID`。

本文用 `H-S01`、`L-C13` 等简称方便阅读：H=human、L=llm、S=sentence、C=claim。**这些简称是本文新增的，不是数据集原字段**；第 9 节给出全部真实 `proposition_id`。

## 2. 阅读两份完整 BHC

这一节只翻译“待核验文本说了什么”，不提前把其中内容判断为正确。

### 2.1 Human-written BHC：完整英文原文

来源：`propositions.csv.gz`，筛选 `subject_id=5954, author_type=human`，读取去重后的 `brief_hospital_course`。

```text
Mr. [**Known lastname 46**] is a 56 year-old male with atrial fibrillation s/p AV
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
his PCP [**First Name8 (NamePattern2) **] [**Last Name (NamePattern1) 1968**] on discharge.

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

### 2.3 本病例的术语小词表

| 英文或缩写 | 本文中的中文意思 |
| --- | --- |
| BHC / Brief Hospital Course | 住院经过摘要 |
| atrial fibrillation / Afib / AF | 心房颤动，简称房颤 |
| s/p | 接受某项治疗或手术之后 |
| AV ablation | 房室结消融；本例其他 EHR 中也写作 AVJ ablation |
| dCHF | 舒张性充血性心力衰竭 |
| PPM / pacemaker | 永久性心脏起搏器 / 起搏器 |
| failure to capture | 夺获失败，即起搏刺激未有效引起心肌兴奋 |
| oversensing | 过度感知 |
| lead / pacer wire | 起搏器电极导线 |
| lead revision | 电极导线修正手术 |
| junctional rhythm / JR | 交界性心律 |
| ventricular paced rhythm | 心室起搏心律 |
| hemodynamically stable | 血流动力学稳定 |
| telemetry | 遥测心电监护 |
| EP lab | 心脏电生理室 |
| CXR / chest X-ray | 胸部 X 线检查 |
| Coumadin | 华法林的商品名 |
| PCP | 初级保健医生 |
| CAD | 冠心病 |
| DDI、VVI | 起搏器的两种模式缩写，本文保留原名 |

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
| `proposition_id` | `b8b6910c-6c77-4e4d-3d5c-763a4a28aca9` |
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
- `CHARTTIME=2112-03-02 11:47:00`
- `CATEGORY=Radiology`，`DESCRIPTION=CHEST (PA & LAT)`


```text
A new pacemaker lead is in appropriate position in the
 right ventricle.
```

**中文：**新的起搏器电极导线在右心室内的位置合适。

**阅读解释：**这与 L-C10 的关键内容“新导线—右心室—位置正确”直接对应。

### 5.2 Not Supported：整个住院期间都没有心律变化

对象：L-C13，医生标签为 `Not Supported`，第一轮两人 NS、一人 NA。

第一段摘录来自 `ROW_ID=401900`，`2112-03-01 02:33:00`，护理进展记录：

```text
On admission to CCU,  HR 70
s Afib.  Pacer interrogated by EP &
   pacemaker rate lowered to 40. Presently in JR.
```

**中文：**入心脏监护病房时，心率为每分钟 70 多次，呈房颤。电生理团队检查了起搏器，并将起搏频率调低至每分钟 40 次。目前呈交界性心律。

第二段来自 `ROW_ID=182001`，`CHARTDATE=2112-03-02`，心电图报告；该行 `CHARTTIME` 为空：

```text
Ventricular paced rhythm.  Atrial mechanism is uncertain.  Since the previous
tracing of [**2112-2-29**] probably no significant change.
```

**中文：**心室起搏心律。心房节律机制不确定。与 2112-02-29 的前次心电图相比，可能没有显著变化。

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

### 6.2 相同病例中的五条真实模型结果

| 编号 | 医生 human_gt | AI verdict | 是否一致 |
| --- | --- | --- | --- |

| L-C10 | `Supported` | `Supported` | 是 |
| L-S06 | `Not Supported` | `Supported` | 否 |
| L-C11 | `Not Supported` | `Supported` | 否 |
| L-C12 | `Not Addressed` | `Not Supported` | 否 |
| L-C13 | `Not Supported` | `Not Supported` | 是 |

注意：这五行包含同一 BHC 的 sentence 和 claim，是用来观察行为的选例，不是独立抽样的性能统计。

下面保留每条记录的完整 `reason` 及翻译。**这是模型自己给出的解释，不是医生意见，也不保证解释正确。**

**L-C10 的模型理由**

```text
The reference context includes a radiology report from 2112-03-02 confirming the new pacemaker lead is correctly positioned in the right ventricle, which supports the text.
```

**中文：**参考上下文包含一份日期为 2112-03-02 的放射报告，确认新起搏器电极导线在右心室内的位置正确，因此支持该文本。

**L-S06 的模型理由**

```text
The text is supported by the reference context as it accurately reflects the patient's stabilization and monitoring on telemetry without significant cardiac rhythm changes, despite some noted complications.
```

**中文：**该文本得到参考上下文支持，因为它准确反映了患者病情稳定、接受遥测监护且没有显著心律变化的情况，尽管记录中提到了一些并发症。

**L-C11 的模型理由**

```text
The text is supported by the reference context as multiple entries confirm telemetry monitoring and the patient's stable condition.
```

**中文：**该文本得到参考上下文支持，因为多条记录确认患者接受遥测监护且病情稳定。

**L-C12 的模型理由**

```text
The reference indicates the patient had pacemaker-related complications, which contradicts the claim of no significant complications.
```

**中文：**参考资料表明患者出现了与起搏器有关的并发症，这与“没有明显并发症”的说法相矛盾。

**L-C13 的模型理由**

```text
The reference context indicates that the patient experienced changes in cardiac rhythm, including junctional rhythm and ventricular paced rhythm, contradicting the statement of no changes.
```

**中文：**参考上下文表明患者经历了心律变化，包括交界性心律和心室起搏心律，这与“没有变化”的陈述相矛盾。

**阅读解释：**模型对整个句子 L-S06 给出 S，对其中的 claim L-C13 给出 NS。整句的理由还出现了“尽管记录中提到了一些并发症”的说法。这个例子值得检查复合句、时间范围和模型解释的一致性，但不能仅凭它断定原子切分一定更好：两次调用的具体上下文并不相同，也没有进行控制变量实验。

### 6.3 reference_payloads 里实际长什么样

以 L-C13 为例，`verdicts.parquet` 中记录的 `reference_id` 为：

`fa1914b787962220e2ba597bc77c25ee03f5f34a83db75a1bed78d39e7c9a649`

通过该值连接 `reference_payloads.parquet`，得到真实送给模型的参考文本。该 payload 有 **100 个编号条目**，开头如下：

```text
Hospital Admission Start: 2112-02-29 18:24:00
Hospital Admission End: 2112-03-02 15:20:00
Electronic Health Record Context
Ordered by Time (Earliest to Latest):
```

**中文：**

- 住院开始：2112-02-29 18:24:00。
- 住院结束：2112-03-02 15:20:00。
- 电子病历参考上下文，按从早到晚的顺序排列。

其中与心律有关的第 74、98 条如下。只展示这两个条目，其他内容没有在本文中展开：

```text
74. Date: 2112-03-01, Time: 07:29:00, Note Category: Physician, Note Description: Physician Resident Progress Note | Text: - patient has junctional rhythm at low 40s, perfusing.  
```
```text
98. Date: 2112-03-02, Time: Unknown, Note Category: ECG, Note Description: Report | Text: Ventricular paced rhythm.  
```

**中文：**

- 第 74 条：2112-03-01 07:29:00，医生进展记录——患者呈交界性心律，心率为每分钟 40 多次的较低范围，仍有灌注。
- 第 98 条：2112-03-02，时间未知，心电图报告——心室起搏心律。

这里的“74”“98”只是当前 payload 内的编号，**不是 NOTEEVENTS 的 `ROW_ID`**。第 98 条可以按内容及日期回查到第 5 节的 ECG 记录；第 74 条的相同文字出现在 `ROW_ID=401915` 和 `401916` 两条 note 中。不能假定上下文中的每个片段都能唯一反查到一条 note。

再看 L-C10 的真实上下文：虽然同样设置 `top_n=100`，实际只有 **99 个编号条目**。其中第 89 条是：

```text
89. Date: 2112-03-02, Time: 11:47:00, Note Category: Radiology, Note Description: CHEST (PA & LAT) | Text: A new pacemaker lead is in appropriate position in the
 right ventricle.
```

**中文：**2112-03-02 11:47:00，放射科胸部正侧位 X 线报告——新的起搏器电极导线在右心室内的位置合适。

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

## 7. 本病例全部 50 条命题：中英对照与医生标签

本节没有过滤无效命题，没有只挑错误样本，也没有重新拆分英文。所有行均来自原始 `propositions.csv.gz`，按 `proposition_id` 连接医生标签和最终有效性字段。

排版顺序：sentence 按其在 BHC 中出现的位置排列；claim 先按来源块位置排列，再保留同一块内在原 CSV 中的行次序。该顺序用于阅读，不意味着数据发布了 claim 的精确原文偏移。

- H=human BHC；L=LLM BHC；S=sentence；C=claim。
- 标签 S=支持；NS=不支持；NA=未涉及。
- 三票顺序对应 `verdict1/2/3`；箭头右侧为 `human_gt`。
- ★ 表示最终 `invalid=True`；其余 48 行均为 False。
- 表格英文将连续空白合并为一个空格，见文首排版说明。

### 7.1 LLM BHC：6 条 sentence

| 编号 | 英文原文与中文翻译 | 医生投票 → 最终标签 |
| --- | --- | --- |
| L-S01 | `The patient was admitted to the hospital after experiencing 5-second pauses due to pacemaker malfunction.`<br>**中：**患者因起搏器故障出现持续 5 秒的心搏停顿后入院。 | S / S / S → **S** |
| L-S02 | `Initial evaluation revealed intermittent failure to capture and oversensing, leading to pacing inhibition, and the pacemaker was reprogrammed.`<br>**中：**初步评估发现起搏器间歇性夺获失败及过度感知，导致起搏被抑制，随后重新设置了起搏器。 | S / S / S → **S** |
| L-S03 | `A chest X-ray suggested possible lead migration, and the patient was planned for overnight observation, reversal of anticoagulation, and lead revision surgery the following day.`<br>**中：**胸部 X 线提示电极导线可能移位，计划让患者留院观察一夜、逆转抗凝作用，并于次日进行电极导线修正手术。 | S / NS / S → **S** |
| L-S04 | `The patient underwent successful lead revision in the electrophysiology lab and was found to have a kinked pacer wire causing the malfunction.`<br>**中：**患者在心脏电生理室成功接受了电极导线修正手术，并发现起搏导线扭折是引起故障的原因。 | NS / S / S → **S** |
| L-S05 | `Post-procedure chest X-ray showed the new pacemaker lead in the correct position in the right ventricle.`<br>**中：**术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。 | S / S / S → **S** |
| L-S06 | `The patient was stabilized and monitored on telemetry throughout his hospital stay, with no significant complications or changes in his cardiac rhythm.`<br>**中：**患者在整个住院期间病情得到稳定，并接受遥测心电监护，未出现明显并发症或心律变化。 | NS / NS / S → **NS** |

### 7.2 LLM BHC：13 条 atomic claim

| 编号 | 英文原文与中文翻译 | 医生投票 → 最终标签 |
| --- | --- | --- |
| L-C01 | `The patient was admitted to the hospital after experiencing 5-second pauses due to pacemaker malfunction.`<br>**中：**患者因起搏器故障出现持续 5 秒的心搏停顿后入院。 | S / S / S → **S** |
| L-C02 | `Initial evaluation revealed intermittent failure to capture and oversensing, leading to pacing inhibition.`<br>**中：**初步评估发现起搏器间歇性夺获失败及过度感知，导致起搏被抑制。 | S / S / S → **S** |
| L-C03 | `The pacemaker was reprogrammed.`<br>**中：**重新设置了起搏器。 | S / S / S → **S** |
| L-C04 | `A chest X-ray suggested possible lead migration.`<br>**中：**胸部 X 线提示电极导线可能移位。 | S / S / S → **S** |
| L-C05 | `The patient was planned for overnight observation.`<br>**中：**计划让患者留院观察一夜。 | S / S / S → **S** |
| L-C06 | `The patient was planned for reversal of anticoagulation.`<br>**中：**计划为患者逆转抗凝作用。 | S / S / S → **S** |
| L-C07 | `The patient was planned for lead revision surgery the following day.`<br>**中：**计划于次日为患者进行电极导线修正手术。 | S / S / S → **S** |
| L-C08 | `The patient underwent successful lead revision in the electrophysiology lab.`<br>**中：**患者在心脏电生理室成功接受了电极导线修正手术。 | NS / S / S → **S** |
| L-C09 | `The patient was found to have a kinked pacer wire causing the malfunction.`<br>**中：**发现患者起搏导线扭折，造成了起搏器故障。 | S / S / S → **S** |
| L-C10 | `Post-procedure chest X-ray showed the new pacemaker lead in the correct position in the right ventricle.`<br>**中：**术后胸部 X 线显示，新起搏器电极导线在右心室内的位置正确。 | S / S / S → **S** |
| L-C11 | `The patient was stabilized and monitored on telemetry throughout his hospital stay.`<br>**中：**患者在整个住院期间病情得到稳定，并接受遥测心电监护。 | NS / S / NS → **NS** |
| L-C12 | `The patient had no significant complications throughout his hospital stay.`<br>**中：**患者在整个住院期间没有出现明显并发症。 | NA / NA / S → **NA** |
| L-C13 | `The patient had no changes in his cardiac rhythm throughout his hospital stay.`<br>**中：**患者在整个住院期间没有心律变化。 | NS / NA / NS → **NS** |

### 7.3 Human BHC：11 条 sentence

| 编号 | 英文原文与中文翻译 | 医生投票 → 最终标签 |
| --- | --- | --- |
| H-S01 ★ | `Mr.`<br>**中：**先生（只有称谓，没有完整陈述）。 | NA / S / NA → **NA** |
| H-S02 | `[**Known lastname 46**] is a 56 year-old male with atrial fibrillation s/p AV ablation and pacemaker placement, dCHF, hypertension transferred for pacemaker revision.`<br>**中：**[姓名已脱敏]，56 岁男性，有心房颤动病史，曾接受房室结消融和起搏器植入，并患有舒张性充血性心力衰竭、高血压，因起搏器修正手术转院。 | S / S / S → **S** |
| H-S03 ★ | `.`<br>**中：**仅一个句点“.”，没有可翻译的陈述。 | NA / NA / NA → **NA** |
| H-S04 | `# pacemaker malfunction: The patient has a history of atrial fibrillation s/p AV ablation and is pacemaker dependent.`<br>**中：**起搏器故障：患者有心房颤动病史，曾接受房室结消融，并依赖起搏器。 | S / S / S → **S** |
| H-S05 | `His pacemaker was failing to capture when he raised his left arm.`<br>**中：**当患者抬起左臂时，起搏器无法有效夺获心肌。 | S / S / S → **S** |
| H-S06 | `He went into a junctional rhythm on the night of his admission when his pacemaker mode was changed to DDI with rate of 40.`<br>**中：**入院当晚，起搏器模式改为 DDI、频率设为每分钟 40 次时，患者出现交界性心律。 | S / S / NS → **S** |
| H-S07 | `He was hemodynamically stable at this rate, and the following day the patient underwent explant of previous pacemaker and inplant of a new right sided pacemaker with a single ventricular lead.`<br>**中：**在这一心率下，患者的血流动力学保持稳定。次日，患者取出了原有起搏器，并在右侧植入了一台带单根心室电极导线的新起搏器。 | S / S / S → **S** |
| H-S08 | `The patient's heartrate increased to 70 paced rythm.`<br>**中：**患者心率升至每分钟 70 次，呈起搏心律。 | NA / NS / NS → **NS** |
| H-S09 | `#Atrial fibrillation: The patient's coumadin was held and 2mg of vitamin K was given in anticipation of his pacemaker procedure.`<br>**中：**心房颤动：为准备起搏器手术，暂停了患者的华法林，并给予 2 mg 维生素 K。 | S / S / S → **S** |
| H-S10 | `He was restarted on his home dose of coumadin to be followed by his PCP [**First Name8 (NamePattern2) **] [**Last Name (NamePattern1) 1968**] on discharge.`<br>**中：**患者恢复了在家服用的华法林剂量，出院后由其初级保健医生[姓名已脱敏]随访。 | NA / NS / NS → **NS** |
| H-S11 | `# CORONARIES: The patient has no history of CAD.`<br>**中：**冠状动脉情况：患者没有冠心病史。 | S / S / S → **S** |

### 7.4 Human BHC：20 条 atomic claim

| 编号 | 英文原文与中文翻译 | 医生投票 → 最终标签 |
| --- | --- | --- |
| H-C01 | `Mr. [**Known lastname 46**] is a 56 year-old male.`<br>**中：**[姓名已脱敏]先生是一名 56 岁男性。 | S / S / S → **S** |
| H-C02 | `Mr. [**Known lastname 46**] has atrial fibrillation.`<br>**中：**[姓名已脱敏]先生患有心房颤动。 | S / S / S → **S** |
| H-C03 | `Mr. [**Known lastname 46**] had AV ablation.`<br>**中：**[姓名已脱敏]先生曾接受房室结消融。 | S / S / S → **S** |
| H-C04 | `Mr. [**Known lastname 46**] had pacemaker placement.`<br>**中：**[姓名已脱敏]先生曾接受起搏器植入。 | S / S / S → **S** |
| H-C05 | `Mr. [**Known lastname 46**] has dCHF.`<br>**中：**[姓名已脱敏]先生患有舒张性充血性心力衰竭。 | S / S / S → **S** |
| H-C06 | `Mr. [**Known lastname 46**] has hypertension.`<br>**中：**[姓名已脱敏]先生患有高血压。 | S / S / S → **S** |
| H-C07 | `Mr. [**Known lastname 46**] was transferred for pacemaker revision.`<br>**中：**[姓名已脱敏]先生因起搏器修正手术转院。 | S / S / S → **S** |
| H-C08 | `The patient has a history of atrial fibrillation.`<br>**中：**患者有心房颤动病史。 | S / S / S → **S** |
| H-C09 | `The patient had AV ablation.`<br>**中：**患者曾接受房室结消融。 | S / S / S → **S** |
| H-C10 | `The patient is pacemaker dependent.`<br>**中：**患者依赖起搏器。 | S / S / S → **S** |
| H-C11 | `The patient's pacemaker was failing to capture when he raised his left arm.`<br>**中：**当患者抬起左臂时，其起搏器无法有效夺获心肌。 | S / S / S → **S** |
| H-C12 | `The patient went into a junctional rhythm on the night of his admission when his pacemaker mode was changed to DDI with rate of 40.`<br>**中：**入院当晚，起搏器模式改为 DDI、频率设为每分钟 40 次时，患者出现交界性心律。 | S / S / NS → **S** |
| H-C13 | `The patient was hemodynamically stable at a rate of 40.`<br>**中：**心率为每分钟 40 次时，患者的血流动力学保持稳定。 | S / S / S → **S** |
| H-C14 | `The patient underwent explant of previous pacemaker and inplant of a new right sided pacemaker with a single ventricular lead the following day.`<br>**中：**次日，患者取出了原有起搏器，并在右侧植入了一台带单根心室电极导线的新起搏器。 | NS / S / S → **S** |
| H-C15 | `The patient's heartrate increased to 70 paced rhythm.`<br>**中：**患者心率升至每分钟 70 次，呈起搏心律。 | NA / NS / NS → **NS** |
| H-C16 | `The patient had atrial fibrillation.`<br>**中：**患者患有心房颤动。 | S / S / S → **S** |
| H-C17 | `The patient's coumadin was held in anticipation of his pacemaker procedure.`<br>**中：**为准备起搏器手术，暂停了患者的华法林。 | S / S / S → **S** |
| H-C18 | `2mg of vitamin K was given to the patient in anticipation of his pacemaker procedure.`<br>**中：**为准备起搏器手术，给患者使用了 2 mg 维生素 K。 | S / S / S → **S** |
| H-C19 | `He was restarted on his home dose of coumadin to be followed by his PCP on discharge.`<br>**中：**患者恢复了在家服用的华法林剂量，出院后由其初级保健医生随访。 | NA / NS / NA → **NA** |
| H-C20 | `The patient has no history of CAD.`<br>**中：**患者没有冠心病史。 | S / S / S → **S** |

## 8. 这位患者的全部参考 EHR 目录

这是 `ehr_noteevents.csv.gz` 中该患者的全部 11 行，而不是只列出上文用到的记录。类别分布为：医生记录 4 条、护理记录 3 条、放射记录 2 条、心电图报告 2 条。没有出院小结，也不包含 human BHC 来源记录 `ROW_ID=21797`。

本病例只含本次住院的参考记录，不能据此推断其他患者也没有历史住院记录。

| ROW_ID | CHARTDATE / CHARTTIME | 原始 CATEGORY / DESCRIPTION | 中文说明 |
| --- | --- | --- | --- |

| `1122601` | 2112-02-29 19:22:00 | `Radiology / CHEST (PORTABLE AP)` | 床旁胸部 X 线报告 |
| `401882` | 2112-02-29 19:39:00 | `Nursing / Nursing Progress Note` | 护理进展记录：入院简要情况 |
| `401883` | 2112-02-29 20:35:00 | `Physician / CCU Fellow addendum` | 心脏监护病房医生补充记录 |
| `401885` | 2112-02-29 20:59:00 | `Physician / Physician Resident Admission Note` | 住院医师入院记录 |
| `182002` | 2112-02-29；时刻为空 | `ECG / Report` | 心电图报告 |
| `401900` | 2112-03-01 02:33:00 | `Nursing / Nursing Progress Note` | 护理进展记录 |
| `401915` | 2112-03-01 07:29:00 | `Physician / Physician Resident Progress Note` | 住院医师进展记录 |
| `401916` | 2112-03-01 07:29:00 | `Physician / Physician Resident Progress Note` | 另一条住院医师进展记录 |
| `401920` | 2112-03-01 10:35:00 | `Nursing / Nursing Transfer Note` | 护理转科记录 |
| `1122851` | 2112-03-02 11:47:00 | `Radiology / CHEST (PA & LAT)` | 胸部正侧位 X 线报告 |
| `182001` | 2112-03-02；时刻为空 | `ECG / Report` | 心电图报告 |

表格保留发布文件中的行次序；没有具体时刻的 ECG 不据此判断当天先后。以上时间是 `CHARTTIME` 或 `CHARTDATE`，不是 `STORETIME`。

`401915` 与 `401916` 的 `TEXT` 在本地文件中完全相同，但 `ROW_ID` 和 `STORETIME` 不同，本文均予以保留。这也说明“原始 note 行”和“不同的文本内容”不是同一统计口径。

## 9. 全部命题 ID 与来源块索引

下表用于回到原始 CSV 定位。H1—H3、L1—L2 是本文给不同 `parent_text_chunk` 添加的简称。

| 本文编号 | 来源块 | proposition_id |
| --- | --- | --- |

| H-S01 | H1 | `c1d52a35-f4f4-8471-1885-85404ec7ed04` |
| H-S02 | H1 | `1a0f3064-1c97-296c-a389-b795ab01d712` |
| H-S03 | H1 | `1263506a-e295-a338-7dd3-a434cb0997bc` |
| H-S04 | H1 | `c84ee607-6ef9-7342-a9dd-ccf8b81353b9` |
| H-S05 | H1 | `10da9283-d042-1122-b62f-c4053b871bd8` |
| H-S06 | H2 | `da0b4b53-d19c-a8cf-6d38-f93898ef1502` |
| H-S07 | H2 | `23de70d6-01ab-d9e6-c473-493787f40875` |
| H-S08 | H2 | `b4067f6f-aa73-949f-4494-a9a293ae6b84` |
| H-S09 | H2 | `370ad90a-88ae-7e2a-a62a-8257b5d60839` |
| H-S10 | H3 | `df86af84-5073-f0bd-b008-69708942c864` |
| H-S11 | H3 | `4be2e77c-134d-8e6e-5207-f1d4f2287930` |
| H-C01 | H1 | `54728b87-9342-ccc6-b446-a75ed5c9f39b` |
| H-C02 | H1 | `f5d9df16-cd00-72a3-d94a-57577dcbd139` |
| H-C03 | H1 | `654e6f50-1287-fb7d-582a-f5e2373641fe` |
| H-C04 | H1 | `35dc092d-2eeb-ac5c-831a-36ec88245c3c` |
| H-C05 | H1 | `939b4652-0927-d0cf-be8c-fdef4a709129` |
| H-C06 | H1 | `8bd305f4-9bef-1b71-fe45-423cdec52e7f` |
| H-C07 | H1 | `0d4aa5e8-fdb8-847f-e2a8-3df51e491da4` |
| H-C08 | H1 | `8c92478b-79de-36f4-b0a1-116437ad959f` |
| H-C09 | H1 | `0128a065-399b-eb11-c256-4762c249c087` |
| H-C10 | H1 | `fa08843f-271c-163a-5406-18920c128732` |
| H-C11 | H1 | `3772f322-326d-c661-227f-6a735dfe0ae0` |
| H-C12 | H2 | `d13824b1-2227-5c4a-0bcd-3e3266e774b6` |
| H-C13 | H2 | `1874e17f-f134-1884-b68f-efd55d43d344` |
| H-C14 | H2 | `b37b45ab-2421-6915-cf2b-822b26be8115` |
| H-C15 | H2 | `f5bd1dd7-3f68-1bb9-4461-6526c0582817` |
| H-C16 | H2 | `8bdaeac9-1d5e-ea32-d43d-47ed43781439` |
| H-C17 | H2 | `890e6ad7-4734-439c-7053-c1b9fc4133d4` |
| H-C18 | H2 | `5a9aefb6-41b5-7777-222a-3faa52d31d1c` |
| H-C19 | H3 | `bec843b8-852c-7261-7a7d-540c4b18e03c` |
| H-C20 | H3 | `22e44a27-be24-6d8a-2787-5fed98edbf80` |
| L-S01 | L1 | `1e719e37-46ea-c0f4-6d92-0ec24a414cd2` |
| L-S02 | L1 | `aaa98c3b-9851-f9a4-8264-5c99ce68ad50` |
| L-S03 | L1 | `52e15866-21b4-b6b8-740f-d646fea47a6b` |
| L-S04 | L1 | `07fbfb51-4bbb-3ce1-29b3-59276761aace` |
| L-S05 | L2 | `13ffe41b-4acc-4878-c0e1-a1fb326b1925` |
| L-S06 | L2 | `f6a39be5-6974-6a98-6955-cb4dcce9be37` |
| L-C01 | L1 | `42769495-9230-956a-a542-d7c143b76c9f` |
| L-C02 | L1 | `68f83966-4830-f139-b1b5-128654b33401` |
| L-C03 | L1 | `0ad92457-8178-740d-d6d7-b31990d14c29` |
| L-C04 | L1 | `a7ddfe7e-6b6e-32e3-c991-2c09bda8b56d` |
| L-C05 | L1 | `76ab9528-db51-0bf6-67da-32796ed136cb` |
| L-C06 | L1 | `fea460b8-09a1-39ec-a08c-8aff859e1706` |
| L-C07 | L1 | `8b1a6764-532f-cb3c-c6e9-c24ced4fac39` |
| L-C08 | L1 | `78369a4b-2334-5cc8-88bc-b184a8091d29` |
| L-C09 | L1 | `3cffe9ed-2bd9-c0a7-1ee1-4b9927b8fc6d` |
| L-C10 | L2 | `e30ebbd3-739d-e3e5-5012-e3959a944486` |
| L-C11 | L2 | `e5cce2ac-86d8-e951-7109-12de09e9a32c` |
| L-C12 | L2 | `e920ecd7-31ea-d103-8ca6-6549c34ac172` |
| L-C13 | L2 | `b8b6910c-6c77-4e4d-3d5c-763a4a28aca9` |

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


