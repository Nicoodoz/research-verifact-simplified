> 阅读镜像：已省略1行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# 075 固定四例批注（API前冻结）

以下英文内容实际加入Judge提示；批注由研究者/Codex依据原reference撰写，不是医生原始解释。原例子、原标签和原reference均保持字节内容不变。

## 示例1：Supported

The patient was extubated without incident.

**核验要求：** The patient was extubated, and that extubation occurred without incident.

- reference #6：`Extubated to np s without incident`；The same extubation event and its uncomplicated course are stated explicitly.

Supported: both components of this proposition are directly present in the example reference. This is a faithful restatement of documented patient information, without adding a new time, cause, measurement, or outcome.

A documented procedure without the outcome qualifier would not automatically establish 'without incident'. Here the qualifier itself is documented; it is not inferred merely from silence about complications.

## 示例2：Not Supported

Pt had a leukocytosis due to pulmonary infarcts.

**核验要求：** Leukocytosis occurred, and pulmonary infarcts caused it. The asserted causal link is part of the proposition, not optional background.

- reference #8：`Leukocytosis: WBC this AM 26.5, down from zenith of 30.2 yesterday.`；The elevated white-cell count itself is addressed.
- reference #8：`Possible etiologies include infection vs. endogenous stress response,`；The note discusses possible explanations; it does not establish the specific claimed cause.

Not Supported: the reference addresses leukocytosis and discusses its etiology, but does not establish that pulmonary infarcts caused it. Supporting the abnormal finding does not support the complete causal proposition. The co-occurrence of pulmonary disease and leukocytosis is not enough to supply the missing causal link.

This does not mean leukocytosis was absent, or that pulmonary infarcts were definitively ruled out. The basis is incomplete support for this addressed causal claim, not an invented contradictory finding. The etiology is explicitly discussed here, unlike a measurement absent from the supplied record.

## 示例3：Supported

Dehydration occurred in the setting of diarrhea and acute infection.

**核验要求：** Dehydration occurred in the setting of diarrhea and acute infection.

- reference #7：`dehydration in the setting of diarrhea and acute infection.`；This association appears explicitly in the physician note.

Supported: the proposition restates the recorded association of dehydration with diarrhea and acute infection. It does not add a specific measurement, a new time, or a claim that one factor is the sole proven cause.

The surrounding note also contains a qualified explanation for renal failure. This example does not justify removing uncertainty from a different causal assertion; only the proposition actually being checked is matched to its supporting text.

## 示例4：Not Addressed


**核验要求：** The posterior superficial compartment was measured, and its pressure was 45 mm Hg.

- reference #2：`Pt presented with left foot compartment syndrome`；Related compartment disease is mentioned, but this is not a pressure measurement for the named compartment.

Not Addressed: the supplied reference discusses compartment syndrome, fasciotomy and postoperative care, but provides no pressure result for the posterior superficial compartment. A diagnosis or an operation cannot substitute for the specific measurement requested by this proposition. Unrelated vital-sign or imaging numbers are not matching evidence.

The reference does not provide a different pressure value for the same measurement, so a conflicting value must not be invented. The conclusion is limited to this measurement being unaddressed in the supplied reference; it does not assert that no measurement occurred anywhere in the patient's full EHR.
