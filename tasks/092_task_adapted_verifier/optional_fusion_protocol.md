# 092唯一允许的条件融合

此文件在任何092正式分类成绩产生前登记。不是自动运行授权：先完成Frozen/Fine-tuned全OOF，按用户条件判断独立模型是否接近强基线、具有少数类/false-S优势或有明显互补。若不存在有价值的独立信号，不运行。

若触发，只对已有B缓存范围测试一次：

`fusion_logits = frozen_B_PriorG_logits + alpha * centered_text_logits + class_bias`。

alpha为一个非负共享标量，范围[0,4]；三类bias和为0，各自由参数范围[-5,5]。优化训练平均普通CE＋0.01×参数平方和，固定L-BFGS-B，不搜正则/阈值/患者subset。匹配的bias-only对照固定alpha=0，训练同样两个自由bias。比较B原规则、bias-only、text fusion；三分数无效保持原B fallback且单列。

每一外层折只使用该折独立模型的最佳checkpoint。融合训练使用该折64名梯度训练患者内有B缓存且分数有效的全部命题，读取该模型对这些训练输入的预测。测试只使用该折20名outer患者的既有OOF logits。**不能使用其他fold的OOF特征来训练本折融合**，因为那些模型可能见过本折outer患者。

训练侧文本logits为in-sample，可能过于自信；此局限明确披露，不以训练融合成绩证明有效。使用同一训练内文本输出是本次简单late-fusion的固定设计，不再追加多层交叉拟合/多个融合器；外层患者始终排除于encoder训练、epoch选择、融合拟合。

触发基于完整OOF研究观察，因此即使每折参数隔离，仍属于本轮探索性扩展，不叫独立确认。完整比较最终质量、类别代价及相对bias-only的救回/伤害；若只达到bias-only水平，不把融合收益归于新增文本信息。没有改默认B、旧PriorG或新设Gate。
