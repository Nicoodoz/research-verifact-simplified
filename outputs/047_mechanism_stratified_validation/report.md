# 047：Mechanism-Stratified Validation

## 核心结论

047没有找到值得扩大到64条患者隔离confirmation的候选方法，按事前停止规则结束。

本轮不是把045/046的16条成功案例重新跑一遍，而是从044另一组10名development患者中固定分出5名screen患者和5名confirmation患者。24条screen在历史base错误/正确各12条的诊断设计下，同期比较三条机制不同的路线：

| 路线 | 正确/24 | rescue | harm | 净变化 | rescue患者 | false-S变化 | 晋级 |
|---|---:|---:|---:|---:|---:|---:|---|
| B：DeepSeek E0 | 12 | — | — | — | — | — | baseline |
| J：同E0换Qwen | 12 | 3 | 3 | 0 | 2 | 0 | 否 |
| P：只重排E0 | 11 | 1 | 2 | -1 | 1 | +1 | 否 |
| S：Qwen选D48短窗→DeepSeek | 12 | 2 | 2 | 0 | 2 | -1 | 否 |

预注册门槛要求净正确至少+2、至少2个rescue且跨至少2名患者、harm最多1、false-S不增加。三条路线均失败，因此冻结的64条confirmation没有执行，也没有事后改门槛救方法。

## 1. 为什么做047

045提示同一C48下换Qwen可在16条定向病例中得到2 rescue / 0 harm，说明部分错误可能是evidence-present-but-misinterpreted。046则发现R3短原文窗在另一批16条上得到2 / 0，但主要rescue的关键事实原本已经存在于E0，更像evidence focusing而不是真正missing-evidence recovery。

这两个信号都来自小型机制screen，不能直接当方法有效。047因此不再扩展更多prompt或检索分支，而是把三个不同假设放到一批不包含045/046成功案例的患者上同期筛选：

- J：证据不变，只换Judge；
- P：模型不变、证据集合不变，只改变已有证据呈现顺序；
- S：保留完整E0，再由语义selector从D48未入选原文中挑证据并追加短窗。

P和S都继续使用原DeepSeek最终Judge；J与B使用相同structured/scoring prompt和相同E0，仅模型名不同。Qwen原生分数没有套用DeepSeek开发的λ=2。

## 2. 数据冻结与患者隔离

047只使用044已经消费过的development材料，不重新读取或评价reserved40。

044 train_cases的10名患者按固定SHA256患者规则排序：
- 前5名只用于24条screen；
- 后5名只用于潜在confirmation。

Screen在044历史OOF结果上固定12条base错误、12条base正确保护样本；先覆盖可用的GT×author格，再固定hash补足，同患者最多6条。历史OOF只用于选诊断样本，所有047方法收益都相对本轮同期新B计算。

另5名患者的64条confirmation在任何047 API结果出现前按患者内hash轮转固定，选择过程不读取GT或历史正确性。它们最终没有被调用。047内部患者隔离成立，但这些都仍属于既往使用过的development患者，因此不是新的外部测试集。

## 3. J：直接换Qwen没有复现045的净收益

J在24条上产生6次标签变化：3 rescue、3 harm，最终正确数仍为12/24，false-S总数与B相同。

这说明045观察到的“同证据换Judge”确实不是完全无效信号：在新的患者材料中Qwen仍能修复若干DeepSeek错误；但它同时破坏了同样数量的原正确判断。收益包含Supported、Not Supported和Not Addressed，不是单纯向某一类偏移；harm也跨类别出现。

因此当前证据支持“Judge差异是真实存在的错误来源”，但不支持把Qwen3.8-27b直接替换DeepSeek-V4-Flash-0731作为总体改进方法。J最适合作为后续错误机制参照，而不是新的默认Judge。

## 4. P：通用“把相关证据放前面”不是有效修复

P完全不增加或删除E0证据块，只按claim token overlap把两块最相关原文移到前部，其余证据保留原相对顺序。

结果只有1 rescue，却产生2 harm；正确数12→11，false-S 3→4，固定DeepSeek U2正确数也从14→12。说明046 R3的信号不能简单推广成“只要把相关内容放得更显眼就会更好”。

这也是一个有用的负结果：evidence-present-but-diluted不能靠通用词项相关性重排稳定解决。相关块可能缺少关系、否定、时间或完整限定，改变位置还可能放大错误相关性。

## 5. S：语义选证有动作，但没有净分类收益

24条selector中17条实际形成了新的短原文窗并触发DeepSeek终判；1条selector输出JSON无效，按协议保留invalid并不重跑。

S得到2 rescue / 2 harm，正确数仍为12/24。false-S从3降到2，但这不是无代价改善，因为同时损失了2条原本正确判断。固定DeepSeek U2仍为14/24，与B完全相同。

## 6. 同期repeat改变了对小样本rescue的解释

6条事前固定的B同输入repeat中有1条发生标签变化：Not Supported→Not Addressed。

这条恰好也是S的两个rescue之一，而且S同样从Not Supported改成Not Addressed并符合GT。因此S的两个表面rescue至少有一个不能可靠归因于新增证据：同一E0在同期repeat里自己就发生了相同方向翻转。

另外，screen中本轮B与用于选样本的044历史base有2/24标签不同。这再次说明跨运行历史答案不能代替同期对照。

P的唯一rescue所在病例，其事前baseline repeat保持原标签不变，因此该单例更像真实输入呈现效应；但P同时产生2个harm并增加false-S，所以仍不构成可扩大的方法信号。

## 7. 成本

实际新API共119次，全部HTTP200：B 24次、B repeat 6次、J 24次、P 24次、S selector 24次、S final 17次。按usage与任务固定单价估算总费用约 **¥2.096631 / ¥8 screen cap**。没有因为预算尚有余量而扩大样本。

## 8. 完整性核验

执行者离线verification共218项检查全部PASS：screen与confirmation患者完全隔离，且都来自development；J与B逐claim请求除模型名外完全一致；P的证据块集合与B一致，只改变顺序及顺序说明。
S追加的每个短窗都能按note和offset逐字回溯到031原始corpus；119个请求均有唯一HTTP200回执，费用低于screen cap；没有confirmation阶段API尝试。

044存在历史源码provenance warning，047没有调用当前044源码重建其历史方法，只读取冻结的train_cases与OOF等artifact。

## 9. 研究决策

047最重要的结果不是又得到一个小样本winner，而是对045/046两个正向线索做了更严格的跨患者复查后，**都没有形成可扩大的净性能信号**。

- “证据已经在E0，换Qwen就更好”只在部分病例成立，直接换Judge产生等量rescue和harm。
- “把已有证据聚焦/前置就更好”没有成立，简单P总体变差。
- “语义选择额外短窗能稳定恢复错误”也没有成立，S净0，且一个rescue与baseline自身repeat翻转重合。

因此不建议下一步直接扩大J、P或S，也不建议把它们组合后再搜索。更可信的下一问题应进一步缩窄为：能否先离线建立**真正的missing-evidence机制集**——明确核心判断信息不在E0、但确实存在于D48或eligible EHR——然后只在这类病例上验证自动恢复；否则“多给相关内容”与“Judge重新权衡已有信息”仍会混在一起。

## 10. 限制

Screen是人为富集的24条诊断集，不代表自然准确率；患者虽与045/046路线screen不同，但仍属于历史development。6条repeat只能揭示本批存在运行波动，不能精确估计总体翻转率。J/P/S的失败只约束本轮冻结实现，不证明所有alternate Judge、evidence focusing或semantic retrieval都无效。

独立审计尚未执行。当前状态应表述为：**047执行完成、执行者核验PASS、无候选过screen门槛、按协议停止confirmation。**
