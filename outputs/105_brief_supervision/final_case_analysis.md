# 105事后源文案例说明

固定转移组内按SHA256(`105/source_cases/v1/`+ID)各选一条，共6条。只用于解释已完成结果，不参与训练/调参，不代表总体频率。核查对象为原claim、生成短理由、引句及其当前reference邻域，不冒充独立医生审核或完整EHR重标。窗口检查以首次字面出现处为起点，指针另保留全部重现位置；不能据此推断模型关注了哪一次出现。全部原文保留私有source_cases_private.json，公开只给抽象关系说明与指纹。

## ef22d89c-9e29-50da-a0ea-c575ddab94e7

natural，GT=Not Addressed；label_only Not Addressed → evidence_brief Not Supported。

目标事件未建立，却仍判NS：理由明确承认缺少目标管理事件，仅引用相关对象的既有清单。符合本轮NA→NS错误模式；不能以对象被提及直接替代具体事件被涉及。理由还含引用本身未提供的类别归属，未据此重标GT。

reference SHA256：`cfb4c64e603f6786a621fd53bca2327935f659415d18cbaf1960e7ba5951224a`；引用位置见final_case_pointers.json。

## 5b053e8a-0621-c567-11db-4d5726a4b602

natural，GT=Supported；label_only Supported → evidence_brief Not Supported。

额外要求显式前后轨迹：引用了操作及后续状态，却以未写明此前状态和完整转变过程拒绝原GT。按冻结标签构成S误伤；这里只审查选中引句及理由，不能独立裁定完整EHR的医学结论。

reference SHA256：`56a7d6c0cd56dcf9959c67afadb3bc0d34e25dfe8d0eae4d17d914b56dbce970`；引用位置见final_case_pointers.json。

## b793439d-2081-e2d7-9300-7f0c490ab42b

pressure，GT=Not Supported；label_only Not Supported → evidence_brief Supported。

发生时点与到达时状态：原文描述事件在此前发生、到达时已处于该状态；理由将其解释为到达时发生。命题语言也有状态/事件歧义，保留原GT，不把该例当作无争议医学重标依据。

reference SHA256：`bc2d1f97ad9686b37d867569745645711158c719805c2498eecd27a2effb4af8`；引用位置见final_case_pointers.json。

## a6b256ba-736c-bf2c-2eec-f1715b8dd7e6

pressure，GT=Not Addressed；label_only Not Addressed → evidence_brief Supported。

从reference头部元数据推断具体事件：理由使用输入中确实存在的住院终点字段，再将其等同于目标事件。字段真实不证明事件类型和对应关系充分。按固定GT是NA→S风险增加，但不能称为凭空编造引句；也不能据此认定医生标签错误。本轮不改GT、不删例。

reference SHA256：`a79aacefaf20ce15be0327ee1baf8ff6b406478ed8dd30b80e4668d4d1d00b02`；引用位置见final_case_pointers.json。

## f59aa50a-969b-93d4-9330-b69383947ba7

natural，GT=Not Supported；label_only Supported → evidence_brief Not Supported。

区分不同评估对象：理由同时引用对原因及另一结局的不同评估，避免把后一否定直接替代前者，按GT由S救回NS。只是单例可解释收益，不抵消总体损失。

reference SHA256：`66ed1c540e7fd946bf4be6e0b1d37e2bdfdfb04b78887893fae4f69584865b9d`；引用位置见final_case_pointers.json。

## 15d5ead5-6d53-ef51-dd5d-84ae14fa50b0

natural，GT=Supported；label_only Not Addressed → evidence_brief Supported。

从直接状态记录救回S：引用当前未见活动性问题及状态稳定的原文，与原GT一致。理由中关于材料不完整的附带语句不能作为额外支持依据；正确标签并不保证整段解释每句话都有必要。

reference SHA256：`5538d85441ac4ee6c493fa3bfaccd558f52ef98c212289ce02994676fd970d6b`；引用位置见final_case_pointers.json。
