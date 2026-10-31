# 示例选择的成熟方法定位

本次仅定向核对原始发表页的摘要与书目信息，没有宣称全文精读。

[Liu等，*What Makes Good In-Context Examples for GPT-3?*，DeeLIO 2022 workshop](https://aclanthology.org/2022.deelio-1.10/)研究从训练池检索与目标语义相近的示例，说明示例选择是已有成熟研究问题。它是ACL关联workshop论文，不是ACL主会；原任务和模型也不同，不能将其收益数字移植到本项目。162目前只做固定训练侧候选与原文节选检查，尚未实现或验证该文的逐病例近邻检索。

[Zhao等，*Calibrate Before Use*，ICML 2021](https://proceedings.mlr.press/v139/zhao21c.html)展示了少样本模型对示例、格式和顺序的敏感性，并提出内容无关输入的校准。它支持谨慎检查类别与示例影响的动机，不能证明本项目存在相同机制或校准有效；当前161是删除检查，162是选例适配，没有把该校准或旧PriorG换名采用，也不声称Conformal保证。

本项目应主张具体、可复核的任务适配收益：同一9B权重和评价ID下，真实训练示例的选择、保留判别依据的节选与token成本控制是否改善MCC、false-S及三类表现。示例提取成功、教师认可或一般文献先例，都不等于分类有效或算法创新。
