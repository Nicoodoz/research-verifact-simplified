> 阅读镜像：已省略47行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# R075｜main｜执行者分析，不是新 GT

A transesophageal echocardiogram (TEE) was performed post-bypass.

原医生标签：Supported

直接观察：claim 与 mixed 完整 body 相同，NS→S 是 LLM 主比较唯一改对；mixed 把 09:20 说成在 13:39 后。另一方面 sentence/local 真的增加 note 89177 [2281,2380) 的 POSTBYPASS 段并给 S。发布 reference 53 已有该段信息。

可能解释：主比较改对不能归因于检索；次比较有可定位的目标段落召回改善，可能来自 post-bypass 与 POSTBYPASS 词形及伴随功能描述匹配。

尚不确定：不能把新 BM25 基线的遗漏说成作者 release 缺证。报告时间也不自动代表整个 TEE 的所有阶段；不要靠错误时钟排序替代 POSTBYPASS 正文。

## 实际检索查询（未发送给最终 Judge）

```json
{
  "claim": "A transesophageal echocardiogram (TEE) was performed post-bypass.",
  "local": ", which required chest tube placement. The patient was also found to have a small right pleural effusion on follow-up chest radiograph. Despite these complications, the patient's condition stabilized, and he was extubated without incident. A transesophageal echocardiogram (TEE) performed post-bypass showed preserved biventricular systolic function. The patient was transferred to the ward on post-operative day 1 and continued to recover, with optimization of medications and advancement of diet as tolerated.",
  "sentence": "A transesophageal echocardiogram (TEE) performed post-bypass showed preserved biventricular systolic function. "
}
```

## 本例关键 EHR 原文

claim reference 6；note 89177 原字符 [0,284)

```text
Indication: Chest pain. Coronary artery disease. Left ventricular function. Preoperative assessment.
Status: Inpatient
Test: TEE (Complete)
Doppler: Full Doppler and color Doppler
Contrast: None
Technical Quality: Adequate

```

claim reference 7；note 89177 原字符 [1402,1654)

```text
I was present in compliance with HCFA regulations. The TEE probe was passed
with assistance from the anesthesioology staff using a laryngoscope. No TEE
related complications.

```

claim reference 8；note 587066 原字符 [0,634)

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

claim reference 9；note 587102 原字符 [634,1269)

```text
   Sodium Chloride 0.9% Flush
   25. Vancomycin
   24 Hour Events:
   Post operative day:
   HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM,

```

sentence reference 12；note 89177 原字符 [0,284)

```text
Indication: Chest pain. Coronary artery disease. Left ventricular function. Preoperative assessment.
Status: Inpatient
Test: TEE (Complete)
Doppler: Full Doppler and color Doppler
Contrast: None
Technical Quality: Adequate

```

sentence reference 13；note 89177 原字符 [1402,1654)

```text
I was present in compliance with HCFA regulations. The TEE probe was passed
with assistance from the anesthesioology staff using a laryngoscope. No TEE
related complications.

```

sentence reference 15；note 89177 原字符 [2281,2380)

```text
There is preserved biventricular systolic function. The exam is unchanged from
prebypass

```

local reference 5；note 89177 原字符 [1402,1654)

```text
I was present in compliance with HCFA regulations. The TEE probe was passed
with assistance from the anesthesioology staff using a laryngoscope. No TEE
related complications.

```

local reference 6；note 89177 原字符 [2281,2380)

```text
There is preserved biventricular systolic function. The exam is unchanged from
prebypass

```

mixed reference 6；note 89177 原字符 [0,284)

```text
Indication: Chest pain. Coronary artery disease. Left ventricular function. Preoperative assessment.
Status: Inpatient
Test: TEE (Complete)
Doppler: Full Doppler and color Doppler
Contrast: None
Technical Quality: Adequate

```

mixed reference 7；note 89177 原字符 [1402,1654)

```text
I was present in compliance with HCFA regulations. The TEE probe was passed
with assistance from the anesthesioology staff using a laryngoscope. No TEE
related complications.

```

mixed reference 8；note 587066 原字符 [0,634)

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

mixed reference 9；note 587102 原字符 [634,1269)

```text
   Sodium Chloride 0.9% Flush
   25. Vancomycin
   24 Hour Events:
   Post operative day:
   HD9
   70M s/p CABG X 3 (LIMA>LAD, SVG>OM,

```

## 发布 reference 对照（不是本轮模型输入）

release reference 46

```text

```

release reference 49

```text
prebypass




```

release reference 51

```text
Test: TEE (Complete)
Doppler: Full Doppler and color Doppler
Contrast: None
Technical Quality: Adequate


INTERPRETATION:

Findings:

RIGHT ATRIUM/INTERATRIAL SEPTUM: No ASD by 2D or color Doppler.



```

release reference 53

```text
There is preserved biventricular systolic function. 

```

## 全部已收到输出（原文）

<details><summary>claim：Not Supported</summary>


```json
{
  "checks": [
    {
      "aspect": "TEE performed",
      "evidence_ids": [6, 7]
    },
    {
      "aspect": "Post-bypass timing",
      "assessment": "Reference 8 indicates CABG on 7-18, and reference 9 shows OR and ventilation times on 7-18, but no explicit link to TEE timing.",
      "evidence_ids": [8, 9]
    },
    {
      "aspect": "TEE indication",
      "assessment": "Reference 6 lists indications including preoperative assessment, not post-bypass evaluation.",
      "evidence_ids": [6]
    },
    {
      "aspect": "TEE details",
      "assessment": "Reference 7 describes TEE performance and no complications, but no bypass context.",
      "evidence_ids": [7]
    },
    {
      "aspect": "Overall",
      "assessment": "The reference confirms a TEE was performed but does not specify it was post-bypass; timing is not established.",
      "evidence_ids": [6, 7, 8, 9]
    }
  ],
  "reason": "The reference documents a TEE on 7-18 and CABG on 7-18, but does not state the TEE was performed post-bypass. The proposition is not fully supported.",
  "verdict": "Not Supported"
}
```

</details>

<details><summary>local：Supported</summary>


```json
{
  "checks": [
    {
      "aspect": "TEE was performed",
      "assessment": "Reference 5 states a TEE was performed and the probe was passed.",
      "evidence_ids": [5]
    },
    {
      "aspect": "TEE was performed post-bypass",
      "assessment": "Reference 6 includes a section labeled 'POSTBYPASS' describing the TEE exam.",
      "evidence_ids": [6]
    },
    {
      "aspect": "TEE findings",
      "assessment": "Reference 6 reports preserved biventricular systolic function, unchanged from prebypass.",
      "evidence_ids": [6]
    },
    {
      "aspect": "No complications",
      "assessment": "Reference 5 notes no TEE-related complications.",
      "evidence_ids": [5]
    },
    {
      "aspect": "Overall support",
      "assessment": "The reference explicitly documents a TEE performed post-bypass, fully supporting the proposition.",
      "evidence_ids": [5, 6]
    }
  ],
  "reason": "The reference confirms a TEE was performed and includes a post-bypass section, directly supporting the proposition.",
  "verdict": "Supported"
}
```

</details>

<details><summary>mixed：Supported</summary>


```json
```

</details>

<details><summary>sentence：Supported</summary>


```json
{
  "checks": [
    {
      "aspect": "TEE performed",
      "assessment": "Reference item 12 states 'Test: TEE (Complete)' and item 13 confirms 'A TEE was performed'.",
      "evidence_ids": [12, 13]
    },
    {
      "aspect": "Post-bypass timing",
      "assessment": "Item 15 explicitly labels a section 'POSTBYPASS' within the TEE report, indicating the exam included post-bypass assessment.",
      "evidence_ids": [15]
    },
    {
      "aspect": "Procedure context",
      "assessment": "Items 10 and 11 mention 'post-CABG' and 'Status post CABG', consistent with bypass surgery, but do not specify TEE timing.",
      "evidence_ids": [10, 11]
    },
    {
      "aspect": "Contradicting evidence",
      "assessment": "No reference contradicts the proposition.",
      "evidence_ids": []
    },
    {
      "aspect": "Overall assessment",
      "assessment": "The reference directly supports that a TEE was performed and includes a post-bypass section, so the proposition is fully supported.",
      "evidence_ids": [12, 13, 15]
    }
  ],
  "reason": "The reference explicitly documents a TEE (item 12) and its performance (item 13), and includes a 'POSTBYPASS' section (item 15), confirming the proposition.",
  "verdict": "Supported"
}
```

</details>

主试验完整输入及发布 reference 见 [冻结病例包](../../packets/R075.json)。补充输入另见 zero_budget_sensitivity_001。
