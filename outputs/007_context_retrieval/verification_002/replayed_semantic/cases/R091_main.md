> 阅读镜像：已省略21行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# R091｜main｜执行者分析，不是新 GT


原医生标签：Not Addressed

直接观察：claim/sentence/mixed 同 body，用 7-19 向病房转移的字段判断 from OSH，分别 NS/S/NS；local 的唯一片段被预算截到 note 587131 前 179 字符，只剩人口学头部，NA 符合 GT。

可能解释：local 的改对不能称找到了正确来源医院，反而是证据变为空泛。模型对 OSH 和脱敏医院字段的对应也不稳定。

尚不确定：Hospital 7453 不能自动判为外院或 CVICU；不恢复真实机构，不将病房转移反向等同入院前转诊。

## 实际检索查询（未发送给最终 Judge）

```json
{
}
```

## 本例关键 EHR 原文

claim reference 1；note 587131 原字符 [3190,3382)

```text
   Cash / Credit cards sent home with:
   Jewelry:
```

sentence reference 1；note 587131 原字符 [3190,3382)

```text
   Cash / Credit cards sent home with:
   Jewelry:
```

local reference 1；note 587131 原字符 [0,179)

```text
   Attending MD:
   Admit diagnosis:
   ACUTE CORONARY SYNDROME
   Code status:
   Height:
   71 Inch
  
```

mixed reference 1；note 587131 原字符 [3190,3382)

```text
   Cash / Credit cards sent home with:
   Jewelry:
```

## 全部已收到输出（原文）

<details><summary>claim：Not Supported</summary>


```json
```

</details>

<details><summary>local：Not Addressed</summary>


```json
{"checks":[{"aspect":"The proposition states the patient was transferred from OSH.","assessment":"The reference does not mention any transfer or OSH.","evidence_ids":[]},{"aspect":"The reference provides admission and discharge dates.","assessment":"Dates are present but do not indicate transfer source.","evidence_ids":[]},{"aspect":"The reference includes attending MD and admit diagnosis.","assessment":"These details do not address transfer origin.","evidence_ids":[]},{"aspect":"The reference includes demographics and code status.","assessment":"No transfer information is included.","evidence_ids":[]},{"aspect":"The proposition is a specific clinical fact.","assessment":"The reference lacks any statement about transfer from OSH.","evidence_ids":[]}],"reason":"The reference contains no information about a transfer from OSH; the claimed fact is not addressed.","verdict":"Not Addressed"}
```

</details>

<details><summary>mixed：Not Supported</summary>


```json
```

</details>

<details><summary>sentence：Supported</summary>


```json
```

</details>

主试验完整输入及发布 reference 见 [冻结病例包](../../packets/R091.json)。补充输入另见 zero_budget_sensitivity_001。
