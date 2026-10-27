# 103逐例转移与源文核查

这是分析后解释性检查，不参与训练、目标选择、答案替换或规则调整。按冻结的哈希排序规则从指定转移组各选2条，共14条；不是随机总体频率估计。全部转移及患者分布另见final_transitions.jsonl和final_patient_transitions.json。

医生GT针对完整参考EHR，发布reference只是模型输入。局部原文核查不裁决GT，也不把词法窗口当完整证据证明。公开仅给ID、抽象关系类型和源文指针；临床原文保留在私有private_case_source_review.json。字符区间为原reference的Python切片[start:end]，SHA可核对原文。

## 8b0ab099-df0f-de9f-04bc-aa9b7b549c97

natural；qwen3.5-9b / lora_label；GT=Supported；Not Supported → Supported。

概括性改善：NS→S救回。窗口存在局部改善描述，但不能仅凭局部原文证明广义总结或模型内部推理。

reference SHA256：`fe58f16871b9d74317e1b2659a0191d1449e1c97fa05004ea9f83d8e9a75e995`；核查窗口：[10985:11311]。

## fd69206d-8b20-7ca8-1b85-faa24d58a95f

natural；qwen3.5-9b / lora_label；GT=Supported；Not Supported → Supported。

重复阴性结果及时间对应：NS→S救回。需区分同一次结果被重复记录与独立多次检查。

reference SHA256：`a450d505ea0e0672d6277d1863ee5edf53afecd7a50c66b4998e320825e885d0`；核查窗口：[770:1095], [1336:1662], [1959:2285], [2959:3286], [3441:3767]。

## 868018da-0e43-4d8b-d797-2fb46897014f

natural；qwen3.5-9b / lora_label；GT=Not Addressed；Not Supported → Not Addressed。

具体结论与主题相关性：NS→NA救回。reference有相关检查及部分结果，不能将本例描述成完全没有相关主题。

reference SHA256：`b8d8dd571804dbfb5d34b7065628ed2c1604a8a5c4b9cca9170e6a7cf720c49e`；核查窗口：[1222:1546], [15676:16000], [16055:16379], [16591:16915], [17160:17484]。

## e18d8cc8-1192-95c2-6f41-246fafa03053

natural；qwen3.5-9b / lora_label；GT=Not Addressed；Not Supported → Not Addressed。

特定事件参与者或内容：NS→NA救回。关键词未命中不等于证明完整EHR不存在；沿医生GT评价。

reference SHA256：`d3f0100b002f4b782167ce27d11d9b54817fcdcd1b3fae6a9754d8317484d1d2`；核查窗口：。

## fef68761-dcf7-fc21-cd06-ea79973fdbae

pressure；qwen3.5-9b / lora_label；GT=Not Supported；Not Supported → Supported。

执行与耐受状态：NS→S误伤。存在操作执行记录，并不完整支持其耐受属性。

reference SHA256：`88d7acbe6487a56d690bb52ba46ae304a156dcc8fafd3bac4873370de09d792f`；核查窗口：[4588:4911], [5353:5676], [7637:7960], [9663:9986], [10682:11005]。

## 92c6deb0-315c-7cb7-7e1e-728e16f0dcb8

pressure；qwen3.5-9b / lora_label；GT=Not Supported；Not Supported → Supported。

药物剂量与因果归因：NS→S误伤。原文有多个可能原因及后续相关用药事件，不能将相关提及等同于完整剂量和因果支持。

reference SHA256：`55690d6ad2006f860d91a65ffc45850f4f6cd9ff19c8aa08de917b71e57e2915`；核查窗口：[529:857], [5161:5488], [11628:11955], [12034:12361], [13835:14161]。

## e088751d-057d-52e0-2867-b8b4a8a6ecd0

natural；qwen3.6-35b-a3b / lora_label；GT=Supported；Not Addressed → Supported。

概括性恢复：NA→S救回。局部改善与持续问题并存，正确GT不能当成推理过程被验证。

reference SHA256：`cc6c5e1c498ea5ed3991486ca0142973b4be2436c1bdadf89800d5b154dd5a5c`；核查窗口：[1605:1931], [2350:2676], [7906:8232], [10776:11102], [11742:12068]。

## d93ff58a-1f26-bcef-fe98-1d9648a50d98

natural；qwen3.6-35b-a3b / lora_label；GT=Supported；Not Supported → Supported。

结果与检查类型归属：NS→S救回。原文多种检查并存，保留GT/reference解释限制，不自行作医学重标。

reference SHA256：`a4e92622a11259ee00ec7ca84b9b73a2a234e774274170429d4b4fe2c38e12ac`；核查窗口：[159:489], [503:833], [956:1286], [19367:19691], [19734:20058]。

## b2cc479c-2006-c198-9824-fa9c8c55c33e

natural；qwen3.6-35b-a3b / lora_label；GT=Not Addressed；Not Supported → Supported。

一般状态与具体亚型：NS→S，错误仍错误但新增false-S。准确率转移会漏掉这种风险升级。

reference SHA256：`e799bfc6ca6b19b7c6780ad5a756bb88de4958bdfa711210f1e0777203d7182e`；核查窗口：[10203:10529], [11306:11632], [13790:14116], [16946:17272]。

## bb7e08e1-0306-29cb-57b8-68a830bff8b9

natural；qwen3.6-35b-a3b / lora_label；GT=Not Addressed；Not Addressed → Supported。

实体和检测结果归属：NA→S误伤。一般状态、其他主体的信息不等于目标检测已执行及其结果。

reference SHA256：`50441044f1b0787820f077a016abdd550db502ef57f604a5370534f0b8c0dec5`；核查窗口：[1432:1758], [2904:3230], [3539:3865], [3975:4301], [4474:4802]。

## 4f09f652-5333-a6b3-e543-5e2e83df67dd

pressure；qwen3.6-35b-a3b / lora_label；GT=Not Supported；Not Supported → Supported。

改善与完全消失：NS→S误伤。原文仍有持续异常，另一个过程的消失不能移用到目标状态。

reference SHA256：`81af47405672f3e485af2ce263226977094b835e0f151fac558aae8d4b52d97e`；核查窗口：[178:507], [2168:2494], [2744:3070], [3288:3614], [3959:4288]。

## 84371107-8b8e-5500-b984-346a37469320

pressure；qwen3.6-35b-a3b / lora_label；GT=Not Supported；Not Supported → Supported。

治疗持续与停止：NS→S误伤。原文仍延续目标治疗，其他治疗停用不能替代目标事件。

reference SHA256：`6a6911f599407ba0e53198b4ad238904537a6469b592cb690d0503ba9b2390ea`；核查窗口：[1767:2094], [2452:2779], [5998:6325], [6881:7215], [7877:8204]。

## e3a6ab59-3080-4660-44c9-f470e743a71e

pressure；qwen3.6-35b-a3b / lora_label；GT=Not Addressed；Not Addressed → Supported。

一般事件与具体内容：NA→S误伤。相关会议或支持信息不完整支持特定场景和内容。

reference SHA256：`bc98a16fbec72f2b2c451863866d62bca211083527c933217b627176bfdfabd6`；核查窗口：[3160:3486], [5540:5866], [6498:6824], [8995:9321], [9329:9655]。

## 4842a6f5-baa3-1361-5b55-4ebc7db410b1

pressure；qwen3.6-35b-a3b / lora_label；GT=Not Addressed；Not Addressed → Supported。

实体出现与事件参与：NA→S误伤。人物角色出现在其他上下文，不证明其参与指定事件。

reference SHA256：`39f7cdd0cf54ab79a57377333a18199a6f4113748accd7bac33db31a4ebb045b`；核查窗口：[2493:2821], [3400:3726], [4777:5103], [5461:5787], [6844:7170]。
