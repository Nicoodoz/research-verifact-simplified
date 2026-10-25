> 阅读镜像：已省略59行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# R095｜main｜执行者分析，不是新 GT

The Left internal Mammary Artery was grafted to Left Anterior Descending.

原医生标签：Supported

直接观察：claim-only 没有 LIMA→LAD 细节，NA；sentence/local/mixed 召回 CABG X3 (LIMA>LAD,...) 的原记录，均 S 符合 GT。全文核对本例发布 reference 100 条，也没有该具体嫁接关系。

可能解释：来源增加 CABG 等周边术语，帮助词面检索连接原 claim 全称与 EHR 缩写，是实际目标关系召回信号。

尚不确定：仍不能证明在原 BGE 检索流程中的增量效果，也不能区分该收益是否可由更好的分词/语义检索直接取得；不是已经验证的普遍重复事件消歧。

## 实际检索查询（未发送给最终 Judge）

```json
{
  "claim": "The Left internal Mammary Artery was grafted to Left Anterior Descending.",
}
```

## 本例关键 EHR 原文

claim reference 12；note 1090183 原字符 [1396,1682)

```text
 and pneumomediastinum.  Lungs are clear, position of the endotracheal tube
 and Swan-Ganz catheter is satisfactory with a left-sided chest drain and
 mediastinal drain.  The NG tube could be advanced 4-5 cm.

```

claim reference 13；note 89177 原字符 [0,284)

```text
Indication: Chest pain. Coronary artery disease. Left ventricular function. Preoperative assessment.
Status: Inpatient
Test: TEE (Complete)
Doppler: Full Doppler and color Doppler
Contrast: None
Technical Quality: Adequate

```

claim reference 19；note 587066 原字符 [0,634)

```text
   Coronary artery bypass graft (CABG)
   Assessment:
   Pt alert and oriented x3 and following all commands/MAE
s.  Pt c/o
   Pt with HR-NSR-80
s-90
s.  Pt with low filling pressures at beginning
   of shift. CI >2.
   LS-CTA/Dim at bases.  Sats 95-100% on 4LO2 NC.  Chest tubes intact
   draining moderate amounts of serosang. drainage.
   Abd. soft with +BS and tolerating clears.
   Foley draining marginal amounts of urine.  Electrolytes monitored and
   repleted.
   BS
s 120
s at beginning of shift.
   Action:
   Pt given a total of 3 liters of

```

sentence reference 10；note 587102 原字符 [0,633)

```text
   HPI:
   HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   EF >55 Wt 79 kg Cr 1.2 HgbA1C 6.0
   PMH none
   Chief complaint:
   PMHx:
   Current medications:
    Acetaminophen 6. Aspirin EC 7. Atorvastatin 8. Calcium Gluconate
   9. Clopidogrel 10. Dextrose 50% 11. Docusate Sodium 12. Furosemide 13.
   Insulin 14. Ketorolac 15. Magnesium Sulfate
   16. Metoclopramide 17. Metoprolol Tartrate 18. Metoprolol Tartrate 19.
   Milk of Magnesia 20. Morphine Sulfate
   21. Oxycodone-Acetaminophen 22. Potassium Chloride 23.

```

sentence reference 11；note 587102 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:

```

sentence reference 12；note 587131 原字符 [0,636)

```text
   Attending MD:
   Admit diagnosis:
   ACUTE CORONARY SYNDROME
   Code status:
   Height:
   71 Inch
   Admission weight:
   79 kg
   Daily weight:
   Allergies/Reactions:
   No Known Drug Allergies
   Precautions:
   PMH:
   CV-PMH:
   Additional history: presented to outside hosp. with confusion,r/i
   nstemi. neuro work up negative,cath-.3vd complicated by rt. common
   femoral av fistula.normal ef.creat.1.0,hgbA1c 6.0%
   rt. femoral av fistula  uneventful o.r. T->preserved

```

sentence reference 13；note 587131 原字符 [1914,2552)

```text
   152
   NURSING NOTE:
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   A&O. Afebrile. Following verbal commands/MAE
s. Speech is clear and
   verbal response is appropriate. LSC with dim bases bilaterally; 4L O2
   sats 95%.  CT intact draining  copious serosanguinous DRG. HCT stable.
   Complies with CDB and I.S. NSR-80
s-90
s. SBP 100-110mmHg. Received IVF
   bolus NS 250cc this am 0900hr.  Abd. soft with +BS and tolerating PO
   clears. Denies N/V. Foley draining marginal amounts of urine.  Delined
   this am. Established IV

```

sentence reference 14；note 587182 原字符 [0,633)

```text
   HPI:
   HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   EF >55 Wt 79 kg Cr 1.2 HgbA1C 6.0
   PMH none
   Chief complaint:
   PMHx:
   Current medications:
    Acetaminophen 6. Aspirin EC 7. Atorvastatin 8. Calcium Gluconate
   9. Clopidogrel 10. Dextrose 50% 11. Docusate Sodium 12. Furosemide 13.
   Insulin 14. Ketorolac 15. Magnesium Sulfate
   16. Metoclopramide 17. Metoprolol Tartrate 18. Metoprolol Tartrate 19.
   Milk of Magnesia 20. Morphine Sulfate
   21. Oxycodone-Acetaminophen 22. Potassium Chloride 23.

```

sentence reference 15；note 587182 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:
```

local reference 9；note 587102 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:

```

local reference 10；note 587131 原字符 [0,636)

```text
   Attending MD:
   Admit diagnosis:
   ACUTE CORONARY SYNDROME
   Code status:
   Height:
   71 Inch
   Admission weight:
   79 kg
   Daily weight:
   Allergies/Reactions:
   No Known Drug Allergies
   Precautions:
   PMH:
   CV-PMH:
   Additional history: presented to outside hosp. with confusion,r/i
   nstemi. neuro work up negative,cath-.3vd complicated by rt. common
   femoral av fistula.normal ef.creat.1.0,hgbA1c 6.0%
   rt. femoral av fistula  uneventful o.r. T->preserved

```

local reference 11；note 587131 原字符 [1914,2552)

```text
   152
   NURSING NOTE:
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   A&O. Afebrile. Following verbal commands/MAE
s. Speech is clear and
   verbal response is appropriate. LSC with dim bases bilaterally; 4L O2
   sats 95%.  CT intact draining  copious serosanguinous DRG. HCT stable.
   Complies with CDB and I.S. NSR-80
s-90
s. SBP 100-110mmHg. Received IVF
   bolus NS 250cc this am 0900hr.  Abd. soft with +BS and tolerating PO
   clears. Denies N/V. Foley draining marginal amounts of urine.  Delined
   this am. Established IV

```

local reference 12；note 587182 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:

```

mixed reference 11；note 587066 原字符 [0,634)

```text
   Coronary artery bypass graft (CABG)
   Assessment:
   Pt alert and oriented x3 and following all commands/MAE
s.  Pt c/o
   Pt with HR-NSR-80
s-90
s.  Pt with low filling pressures at beginning
   of shift. CI >2.
   LS-CTA/Dim at bases.  Sats 95-100% on 4LO2 NC.  Chest tubes intact
   draining moderate amounts of serosang. drainage.
   Abd. soft with +BS and tolerating clears.
   Foley draining marginal amounts of urine.  Electrolytes monitored and
   repleted.
   BS
s 120
s at beginning of shift.
   Action:
   Pt given a total of 3 liters of

```

mixed reference 12；note 587102 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:

```

mixed reference 13；note 587182 原字符 [5147,5785)

```text
   WBC
   20.4
   13.9
   16.0
   Hct
   32
   33
   32.0
   33.1
   31.4
   29.5
   Plt
   175
   174
   172
   Creatinine
   0.8
   0.8
   TCO2
   28
   26
   24
   25
   Glucose
   143
   122
   129
   129
   81
   132
   124
   Other labs: PT / PTT / INR:15.8/61.7/1.4, Lactic Acid:1.1 mmol/L
   Assessment and Plan
   CORONARY ARTERY BYPASS GRAFT (CABG)
   Assessment and Plan: HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA) repair right groin AV
   Neurologic: Neuro checks Q: 4 hr, PCT/Torodol prn pain. OOB.PT eval
   Cardiovascular:

```

## 发布 reference 对照（不是本轮模型输入）

release reference 23

```text
 

```

release reference 26

```text
 evaluate for pseudoaneurysm or fistula.

 

```

release reference 68

```text
There is preserved biventricular systolic function. 

```

release reference 69

```text
   Assessment:
   Pt alert and oriented x3 and following all commands/MAE
s.  Pt c/o
   

```

release reference 83

```text
   Attending MD:
   Admit diagnosis:
   ACUTE CORONARY SYNDROME
   Code status:
   Height:
   71 Inch
   Admission weight:
   79 kg
   Daily weight:
   Allergies/Reactions:
   No Known Drug Allergies
   Precautions:
   PMH:
   CV-PMH:
   Additional history: presented to outside hosp. 

```

release reference 84

```text
   function.
   

```

release reference 91

```text
   Plavix 2'poor targets per RH
   Pulmonary: IS, Encourage DB&C,IS
   Gastrointestinal / Abdomen:
   Nutrition: Regular diet, Advance diet as tolerated , Cont bowel
   regiment, prophylaxis
   Renal: Foley, Adequate UO, Start gentle diuresis. 

```

## 全部已收到输出（原文）

<details><summary>claim：Not Addressed</summary>


```json
{"checks":[{"aspect":"Proposition states LIMA grafted to LAD","assessment":"Reference mentions CABG x3 and status post CABG but does not specify graft vessels or LIMA-LAD anastomosis.","evidence_ids":[19,12]},{"aspect":"Reference addresses CABG surgery","assessment":"Confirms CABG was performed on 7-18, but no graft details are provided.","evidence_ids":[19,12]},{"aspect":"Reference addresses LIMA or LAD","assessment":"No mention of Left Internal Mammary Artery or Left Anterior Descending artery in the reference.","evidence_ids":[]},{"aspect":"Reference supports complete proposition","assessment":"The specific LIMA-to-LAD graft is not documented; only generic CABG status is noted.","evidence_ids":[12,19]},{"aspect":"Reference contradicts proposition","assessment":"No contradictory information exists; the reference simply lacks the specific graft detail.","evidence_ids":[]}],"reason":"The reference confirms CABG surgery but does not mention the LIMA or LAD, so the proposition is not addressed.","verdict":"Not Addressed"}
```

</details>

<details><summary>local：Supported</summary>


```json
{
  "checks": [
    {
      "aspect": "LIMA grafted to LAD",
      "assessment": "Reference states 'CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA)' in notes 9, 10, 11, and 12, directly supporting the proposition.",
      "evidence_ids": [9, 10, 11, 12]
    },
    {
      "aspect": "Procedure performed",
      "assessment": "Reference confirms CABG surgery occurred on 7-18, with LIMA>LAD as one of the grafts.",
      "evidence_ids": [9, 10, 11, 12]
    },
    {
      "aspect": "No contradictory information",
      "assessment": "No reference material contradicts the proposition.",
      "evidence_ids": []
    },
    {
      "aspect": "Relevant context",
      "assessment": "Reference provides sufficient detail on the CABG procedure, including graft types and targets.",
      "evidence_ids": [9, 10, 11, 12]
    },
    {
      "aspect": "Overall support",
      "assessment": "The proposition is fully supported by multiple consistent references.",
      "evidence_ids": [9, 10, 11, 12]
    }
  ],
  "reason": "The reference explicitly documents 'CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA)' in multiple notes, confirming the LIMA was grafted to the LAD.",
  "verdict": "Supported"
}
```

</details>

<details><summary>mixed：Supported</summary>


```json
{
  "checks": [
    {
      "aspect": "LIMA grafted to LAD",
      "assessment": "Physician note states 'CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA)'.",
      "evidence_ids": [12, 13]
    },
    {
      "aspect": "Left internal mammary artery used",
      "assessment": "LIMA abbreviation in note confirms left internal mammary artery.",
      "evidence_ids": [12, 13]
    },
    {
      "aspect": "Graft target is LAD",
      "assessment": "Note explicitly lists LIMA>LAD, indicating LAD as target.",
      "evidence_ids": [12, 13]
    },
    {
      "aspect": "Procedure performed",
      "assessment": "Notes confirm patient underwent CABG x3 on 7-18.",
      "evidence_ids": [11, 12, 13]
    },
    {
      "aspect": "No contradicting evidence",
      "assessment": "No reference contradicts the proposition.",
      "evidence_ids": []
    }
  ],
  "reason": "The physician notes explicitly document 'CABG X 3 (LIMA>LAD, SVG>OM, SVG>PDA)', confirming the LIMA was grafted to the LAD.",
  "verdict": "Supported"
}
```

</details>

<details><summary>sentence：Supported</summary>


```json
{"checks":[{"aspect":"LIMA graft to LAD","assessment":"Reference states CABG x3 with LIMA>LAD in multiple notes.","evidence_ids":[10,11,12,13,14,15]},{"aspect":"Graft type","assessment":"LIMA explicitly named as conduit to LAD.","evidence_ids":[10,11,12,13,14,15]},{"aspect":"Target vessel","assessment":"LAD explicitly named as target.","evidence_ids":[10,11,12,13,14,15]},{"aspect":"Procedure context","assessment":"CABG performed on 7-18, consistent with proposition.","evidence_ids":[10,11,12,13,14,15]},{"aspect":"Contradictions","assessment":"No conflicting information found.","evidence_ids":[]}],"reason":"The reference repeatedly documents LIMA>LAD as part of CABG x3, fully supporting the proposition.","verdict":"Supported"}
```

</details>

主试验完整输入及发布 reference 见 [冻结病例包](../../packets/R095.json)。补充输入另见 zero_budget_sensitivity_001。
