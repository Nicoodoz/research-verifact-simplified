# N264核验目标保真的补充独立核查

按主线程补充要求，本线程另读N264三组完整输出、claim、parent、原医生记录、有效性记录及两套reference中的enteric-coated对应完整块。不扩大其他案例。

直接观察：正式claim确为“The patient is not enterically coated.”；parent是“Per patient, not enterically coated and would not anticipate levels to further rise.”。原医生三票均Not Supported，最终GT仍NS；数据集中invalid=False，不能由执行者自行剔除。

三组均判S且公开解释都转向ASA。O完整reasoning_chain先正确复述原claim，随后写“which likely refers to ASA (aspirin) tablets”，最终用ASA未肠溶包衣支持；V的claim_summary明确“referring to the aspirin (ASA) ingested”；C的Claim summary直接改写为“the patient's aspirin (ASA) was not enteric coated”。实际reference确有ASA的原文：发布块12/45及C块3“The ASA were not enteric coated.”。

因此，“三套输出都把核验对象解释为ASA而非原claim字面主语patient，并与正式NS标签不一致”有直接材料依据。“共享的核验目标保真问题”作为解释类别没有越界，也不属于仅C48检索造成的问题，因为在同一发布reference下O/V同样发生。更严格的措辞是**输出展示了目标替换/善意修复**；这不证明隐藏内部机制，也不能估计其总体发生率。

仍需保留：parent语法显示可能存在上游命题化缺陷，但本次没有完整重放原claim生成过程，不能断言具体生成器如何产生错误。原患者病历ASA事实可以真实存在，却不能让执行者修改正式claim或将新目标沿用原GT。这里不重新标医学GT，也不建议将该样本事后设invalid。
