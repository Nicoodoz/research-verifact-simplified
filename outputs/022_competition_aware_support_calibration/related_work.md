# 022定向相关工作核对

核对日期2026-09-19；仅用于定位已有方法，不是文献首创性穷尽检索。

| 既有研究 | 与022的关系及区别 |
|---|---|
| [Guo et al., ICML 2017](https://proceedings.mlr.press/v70/guo17a.html) | 研究后处理校准及temperature scaling。022保留温度对照：正温度不改变argmax，只用概率指标解释其作用；vector scaling是已有校准参照，不能改名声称创新。 |
| [Kull et al., NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/8ca01ea920679a0fe3728441494041b9-Abstract.html) | Dirichlet calibration使用对数概率、线性映射与softmax，强调多类概率指标。022对生成的三个整数评分做log与后处理，输入不是神经网络原生logits，尚未验证为概率；本轮V是对角vector scaling，不冒称实现全Dirichlet矩阵模型。 |
| [Zhao et al., ICML 2021](https://proceedings.mlr.press/v139/zhao21c.html) | contextual calibration通过无内容输入估计提示下的答案偏置；022没有新增无内容探针，而是用医生claim标签、患者分折监督拟合少量参数。二者实验问题和信息来源不同。 |
| [Reif & Schwartz, NAACL 2024](https://aclanthology.org/2024.naacl-long.378/) | 多任务、多模型研究label bias及缓解；不能把其标签偏置结论直接当临床支持偏保守的内部机制证明，也不能仅以PA衡量偏置问题已解决。 |
| [Dawkins & Nejadgholi, ACL 2022](https://aclanthology.org/2022.acl-short.59/) | region-dependent temperature scaling说明按输出区域条件化的校准并非全新概念；其token任务与温度形式不等同022的NS/NA双偏置。未据该论文宣称本公式已有或尚无完全相同先例。 |
| [scikit-learn分组交叉验证说明](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data) | 同组样本不能横跨拟合与验证。022把患者的作者、轮次和服务共同绑定；固定正则化，无内层超参搜索，避免外层患者标签参与选择。 |

022可检验的具体问题是：在API-BGE固定、原三类评分不变的临床claim核验中，NS/NA相对竞争是否提供超过全局偏置/普通校准的患者折外价值。它是有标签的轻量后处理，不是完全training-free，也不微调基础LLM。阶段A结果没有支持结构升级，故不主张公式或应用方法首创，不为包装贡献扩大实验。
