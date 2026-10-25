"""Create a new complete Chinese manuscript; never overwrite task 091."""
import re,os
import common092 as c
from supplement092 import metric_table
def main():
    source=c.ROOT/'outputs/091_integrated_evidence_decision_study/manuscript_zh.md'
    text=source.read_text(encoding='utf-8-sig')
    # Rebase all inherited local links before inserting new task-092 sections.
    def link(m):
        target=m.group(2)
        if '://' in target or target.startswith('#'):return m.group(0)
        path=(source.parent/target).resolve()
        return '['+m.group(1)+']('+os.path.relpath(path,c.OUT).replace('\\','/')+')'
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)
    text=text.replace('# 临床事实核验中的证据信息、模型判定与决策边界：分类质量、错误支持和成本的受控实证研究','# 临床事实核验的任务适配与决策边界：基于患者记录的分类质量、错误支持和成本研究',1)
    opening='匿名中文完整研究稿，2026-09-27。基于091完整稿新增任务适配文本核验器的患者分组交叉验证及唯一条件融合；原091稿保持不变。历史冻结确认、反复暴露开发材料和新增100患者OOF分别呈现，不合并证据等级。作者及投稿格式待投稿阶段确定，实验章节均对应已运行结果。'
    first=text.index('\n\n');second=text.index('\n\n',first+2)
    text=text[:first+2]+opening+text[second:]
    abstract="""## 摘要

临床事实核验既受患者证据覆盖影响，也受模型表示和最终决策边界影响。本文在VeriFact-BHC上固定证据或模型输出，比较边界修正、示例与模型替换，并新增一个直接读取命题及检索EHR的任务适配文本核验器。该核验器采用完整宽度窗口表示与注意力聚合，以医生三分类标签监督DeBERTa顶部一层；相同输入、聚合头和训练预算的冻结编码器作为核心对照。在100名患者9065条有效原子命题的五折患者分组预测中，微调使正确数由7204增至7530，PA由79.47%增至83.07%，MCC由0.4433增至0.5156，错误支持由764降至745；收益主要来自真Supported恢复。相比原VeriFact的7331条正确和0.4959 MCC，微调的PA更高，但Not Supported召回仅8.95%，错误支持更多。已有生成式系统共同956条上，微调模型独立修对66条无示例系统错误、同时误伤79条；一次预登记融合取得795条正确，较原系统增加12条但错误支持增加23条，未形成综合升级。融合相对匹配的偏置对照增加9条正确、减少15条错误支持，提供有限文本增量信号。历史保留患者边界实验和示例压缩诊断同样显示，原生或总体指标改善可能伴随非支持类损失。结果支持任务监督更新文本表示的受控开发价值，同时要求将分类收益、错误支持、决策偏置和计算成本分别报告；本研究不提供新外部测试或临床安全性保证。

**关键词：** 临床事实核验；电子病历；任务适配；患者分组交叉验证；错误支持；决策融合

"""
    start=text.index('## 摘要');end=text.index('## 1 引言')
    text=text[:start]+abstract+text[end:]
    text=text.replace('本文回答四个研究问题。','本文回答五个研究问题。',1)
    anchor='该问题也影响核验器作为训练信号的可靠性，以及何时应暂缓自动接受一项命题。'
    text=text.replace(anchor,anchor+'另一个尚需受控检验的问题是：在固定检索包上，直接用医生标签更新文本encoder，能否提供既有生成式分数之外的信息，而不依赖新的示例或后处理搜索？',1)
    anchor='RQ4：在缺少有限证据充分性gold的条件下，一个窄范围、可观察的证据缺口能否支持有意义的选择性核验试验？'
    text=text.replace(anchor,anchor+'RQ5：同输入和聚合头下，医生监督更新文本encoder是否改善患者外分类，并能否通过一次受控融合增加生成式系统的效用？',1)
    text=text.replace('它们共同构成实证论文，而非一个已经证明普遍优越的复合算法。','新增贡献是完整患者覆盖的冻结/微调文本核验对照、类别收益分解及带偏置对照的有限融合验证。它们共同构成有实际模型工作的实证论文，而非一个已经证明普遍优越的复合算法。',1)
    related="""### 2.4 临床自然语言推断与任务适配

MedNLI已经提供医生标注的临床自然语言推断数据，并研究迁移学习[12]。本文不主张首次用医生标签训练文本核验器。我们复用既有DeBERTaV3模型家族[13]及NLI checkpoint，研究完整记录标签监督有限检索包的分类效果；NLI原分类头不参与预测，entailment等标签不直接映射为本任务GT。MedNLI与其他外部数据集未作为本轮实测基线，其论文数字不与本研究交叉验证直接比胜负。注意力聚合、部分解冻及线性融合均为既有操作，方法价值来自严格控制输入与监督后的实测增量和限制。

"""
    text=text.replace('## 3 任务与研究框架',related+'## 3 任务与研究框架',1)
    method="""### 3.4 读取患者证据的独立任务适配核验器

给定命题x及固定C48文本E，将E按512-token模型上下文切为连续窗口，每窗保留完整x与pair特殊符号，证据重叠32 token。所有E token至少出现一次，不通过已知GT选择窗口。前23层固定，末层输出完整1024维CLS向量h_j。令u_j=LayerNorm(h_j)，a_j=softmax(wᵀu_j+b)，聚合v=Σ_j a_j u_j，再经dropout和线性头得到三类logits。模型只读取原文，不读取LLM label_scores、reason、医生标签token或PriorG。

Frozen只更新聚合和分类头；Fine-tuned还更新第24个Transformer block，共享相对位置embedding固定。两者窗口、头、损失、患者和预算相同；普通交叉熵监督的唯一主消融是顶部block是否更新。固定底层激活仅减少重复计算，不是标签驱动的选证或32维随机投影。该设计与早期032冻结NLI编码、随机投影和依赖旧分数的残差模型不同，但032因结构/输入不同不作为本轮核心消融。

仅在独立文本模型表现接近强基线、少数类较好或有明确互补错误时，测试一次生成式—判别式融合。令z_B为冻结B的PriorG log-score，t为文本logit，融合为z_B+α(t−mean(t))+b，α∈[0,4]；b的两个自由参数限于[−5,5]，第三个为负和。固定CE与0.01参数平方惩罚；匹配bias-only设α=0，用来区分文本增量和重新改变类别偏置。没有新增Gate或多个融合器搜索。

"""
    text=text.replace('## 4 实验设计',method+'## 4 实验设计',1)
    text=text.replace('该组随后已有事后分析，本轮只引用正式汇总，不用于新方法开发、选参或案例诊断。','该组随后已有事后分析。091仅引用正式汇总；新增任务适配实验依据用户明确授权使用全部100名患者标签做新的患者分组CV，不能将这些材料重新称为未接触测试集。',1)
    text=text.replace('|压缩（089、090）|','|任务适配（092）|100/9065；B/F4共同24/956|冻结/微调文本核验与一次条件融合|全部患者已有研究暴露；患者分组OOF，不是新外部验证|\\n|压缩（089、090）|'.replace('\\n','\n'),1)
    design="""### 4.4 任务适配的全量患者分组评价

9065条有效atomic claim包含S7035、NS693、NA1337，human5624、LLM3441。原invalid30条排除，GT不改。7248条复用已有C48，1817条用冻结管线的本地BGE实现补齐；后者不声称与API逐字等价，两臂使用同一输入，并按来源分层。没有跨患者完全相同的claim/reference组合，单独claim有重复；325条时间元数据冲突保留，不按模型对错过滤。

五折外层各20名患者，内部64人训练、16人选epoch。训练5轮，AdamW头lr1e-3、末层lr2e-5，weight decay0.01，梯度裁剪1，有效batch8，head dropout0.1；seed92027+fold。按内部验证MCC、PA、Macro-F1及较少false-S顺序选epoch，直接输出外层，不再用80人重训。只测普通CE、顶部单层微调，不追加loss/骨干搜索。

原作者按全9065相同ID重算；B/F4共同956条采用冻结来源优先级和原fallback，935条双方核心有效及排除示例患者后的924条另表。历史共同集混合选样，不冒充自然总体；旧B/F4的校准和示例暴露不自动获得新五折隔离保证。新增文本训练与融合参数严格排除外层患者。融合训练特征取同折64名训练患者中的B缓存，不能用其他折OOF特征产生间接泄漏；训练特征为in-sample的局限明确保留。

全部云端权重哈希、输入和源码与本地核对；实际运行环境为RTX4090、Python3.12.3、torch2.8.0+cu128。初始冻结文件所记RTX3060环境仅对应本地准备。跨硬件数值桥接和部署检查不算第二次独立训练重复。

"""
    text=text.replace('## 5 结果',design+'## 5 结果',1)
    met=c.read(c.OUT/'metrics.json');fus=c.read(c.OUT/'fusion_supplement.json')
    results="""### 5.8 任务适配改善了冻结模型，但没有消除类别代价

**表6　100名患者9065条全量OOF。** Original为相同ID发布预测；Frozen/Fine-tuned均为独立原文模型，无LLM分数或PriorG。

"""+metric_table(met['full_OOF'])+"""

微调相对冻结603救回、277伤害，净+326；S/NS/NA净正确分别+311/+17/−2。五折PA与MCC均提高，患者84胜/8负/8平，患者净差中位数+3，最大+11；收益不是单个患者制造。固定预测患者bootstrap的PA差95%区间为[+2.86,+4.36]个百分点，MCC差[+0.0565,+0.0887]。这些区间不覆盖重训、选模或历史开发不确定性。

微调S/NS/NA召回为93.56%/8.95%/66.27%，冻结为89.14%/6.49%/66.42%，原作者为91.74%/49.06%/40.16%。相对原作者净+199正确包含S+128、NS−278、NA+349；错误支持增加172。微调的PA更高，MCC点值较高但差值区间[−0.0061,+0.0462]跨0，Macro-F1反而降低。这不能被表述为全面优于原VeriFact。

![全量三类混淆矩阵](confusion_matrices.png)

human部分微调较冻结净+198、false-S−29；LLM部分净+128、false-S+10，且LLM部分MCC0.2226低于原作者0.3057。NLL与Brier改善而ECE15由0.0207升至0.0646，不能称全面校准改善。类别和来源分层见附录D。

### 5.9 有限融合识别出文本信号，但未达到综合升级

**表7　已有B/F4共同956条，不与表6跨分母比胜负。**

"""+metric_table(fus['metrics'])+"""

Fine-tuned相对B独立修对66条、误伤79条，满足事前允许的一次互补验证条件。五折融合α约0.645、1.538、0.321、0.618、0.205，均未靠评价集改参数。融合较B净+12包含S+22、NS−7、NA−3；错误支持多23条，MCC略降，PA与MCC差区间均跨0。融合仅比F4多2条正确而多12条错误支持，不能升级默认。

与匹配的bias-only相比，文本融合19救回/10伤害，净+9，false-S少15条；S净−6、NS+5、NA+10。MCC差+0.0396，固定预测患者区间[+0.0015,+0.0769]；PA差区间[−0.52,+2.30]个百分点跨0。该结果支持有限的文本条件增量，而非将所有收益归于重调S偏置；触发条件看过本轮OOF、融合训练特征为in-sample、历史缓存反复暴露，故仍是探索性证据，不作独立确认性声明。

本地原文在线编码的12条固定样本，Frozen/Fine平均约0.351/0.333秒，均与云端标签一致；不含C48检索、冷启动，不能以小样本时延差证明微调加速。完整核验器约4.34亿参数，52.51MB每折保存文件只是末层和头，需要原backbone。云端编码与十组模型记录阶段合计约81.6分钟，不是租赁账单；新增API为0，GPU租金未知。后续停在本次固定版本，不因NS短板追加类别平衡loss或新融合。

"""
    text=text.replace('## 6 讨论',results+'## 6 讨论',1)
    text=text.replace('## 7 局限与可复现性','任务适配提供了区别于再调分数的新受控证据：原文encoder确实由医生监督更新，并改善同结构冻结基线。然而收益主要落在S；少数类短板和融合风险说明“可训练”与“可升级”是不同结论。我们保留这一模型贡献，同时拒绝用总体PA掩盖NS召回损失，也不把有限融合的探索性区间当临床部署证明。\n\n## 7 局限与可复现性',1)
    text=text.replace('## 8 结论','新增任务适配覆盖全部100名已暴露患者。外层患者隔离只保护该折参数训练和epoch选择，不能消除整个研究历史的选择偏倚；单种子、顶部单层、普通CE的结果不外推到所有微调策略。GT面向完整参考EHR，实际训练输入是有限C48，局部来源核查没有产生新充分性gold。云端训练由用户完成，权重、环境、源码和输出已本地核查，但未取得完整远端控制台日志，不能声称对云端每个步骤进行了独立审计。\n\n## 8 结论',1)
    a=text.index('## 8 结论');b=text.index('## 参考文献')
    conclusion="""## 8 结论

临床事实核验应沿证据、原生判定、分数边界和任务表示分别评价。历史保留患者实验证明固定边界收益伴随错误支持代价；示例压缩原生净收益被后处理缩小，选择性核验原型因材料不足未进入分类实测。新增患者分组OOF表明，在同输入与聚合头下，医生监督更新encoder顶部一层能够提高PA、MCC和Macro-F1，但主要恢复真S，尚未解决NS识别。一次带偏置对照的融合提供有限文本增量，却未超过现有系统的综合风险表现。可主张的是具有完整模型实现和全量OOF支撑的受控任务适配证据，而不是已确认的新默认系统、通用算法首创或独立外部泛化。

"""
    text=text[:a]+conclusion+text[b:]
    refs="""12. Romanov A, Shivade C. Lessons from Natural Language Inference in the Clinical Domain. EMNLP, 2018. [官方页面](https://aclanthology.org/D18-1187/)。
13. He P, Gao J, Chen W. DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing. arXiv:2111.09543. [原论文页面](https://arxiv.org/abs/2111.09543)。

"""
    text=text.replace('## 附录A',refs+'## 附录A',1)
    text+="""
## 附录D：任务适配模型的可核查产物

[完整报告](report.md)、[模型架构](architecture.md)、[全量与共同集指标](metrics.json)、[完整类别/矩阵/分层表](detailed_tables.md)、[患者配对区间](paired.json)、[融合及偏置对照](fusion_results.json)、[融合分层](fusion_supplement.json)、[病例分析](case_analysis.md)、[成本](final_costs.json)和[云端来源核对](cloud_training_manifest.json)均对应本轮实际运行。历史091正文链接保持指向其原工件，不覆盖原稿。公开权重SHA、ID与指标；临床原文、私有权重和激活不随论文公开。
"""
    (c.OUT/'manuscript_zh.md').write_text(text,encoding='utf-8')
    evidence="""# 研究问题—方法—证据—限制

|问题|方法|主要证据|限制与主张边界|
|---|---|---|---|
|固定边界能带来多少收益/代价|036 U0/U2、Gate和标准校准同分数比较|历史3571共同有效确认表，保留StdM/StdV和原作者同ID|仅对应早期配置，不继承为当前T-S/092最终验证|
|当前系统哪些环节有用|078受控消融；084—090示例、压缩、模型替换|091完整稿原章节与对应报告；prior-only/PriorG同标签事实保留|已暴露开发队列，各分母分开，不声称四个独立创新组件|
|原生收益为何不转为最终收益|091对090标签/评分/边界逐例诊断|raw净+7变final净+2的分解|不是模型内部推理证明，不因区间跨0称等效|
|是否可做有限证据选择性核验|091单一数值—单位原型、盲盘点|17条/8人，缺口4条/3人，不足预定材料门槛|没有分类实测或新医生充分性gold，不能冒充方法阴性|
|RQ1 顶层微调是否增加效用|092同输入/窗口/聚合/监督预算，冻结对微调|9065 OOF净+326；PA/MCC区间正，false-S−19|仅顶部单层、普通CE、一个种子；非外部测试|
|RQ2 收益来自哪些类|全量类别转移、author/患者/fold分层|S+311、NS+17、NA−2；NS召回8.95%|病例只是可见材料复查，不证明语义机制|
|RQ3 相对强基线的位置|原作者全量同ID；B/F4缓存共同956|原作者7331对Fine7530；共同B783/F4793/Fine770|分母不同不能跨表比胜负；Fine的NS及false-S短板不隐藏|
|RQ4 是否含旧分数之外的信息|唯一α文本融合和匹配bias-only，同折训练与outer隔离|融合795、bias786；false-S64对79；MCC差区间正|PA差区间跨0；触发已看OOF、训练特征in-sample、无新独立确认|
|成本与可复现性|云权重/源码/输入哈希；本地在线原文推理|10份最佳权重可加载；956数值桥接0标签差，12条在线检查|不是重训稳定性；云租金未知，0API≠0计算成本|

092提供可写入方法和结果的训练研究贡献，但默认仍为B＋Frozen PriorG。未自动开展093、重训PriorG、扩大示例/阈值/模型搜索。自检是执行者自检，独立审计未执行。
"""
    (c.OUT/'evidence_map.md').write_text(evidence,encoding='utf-8')
    print('Complete new manuscript and evidence map written; 091 unchanged.')
if __name__=='__main__':main()
