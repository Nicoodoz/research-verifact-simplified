# 106最小标签目标诊断的实现

最终唯一GPU准备方案为同104原196条的`label_mean`与`label_sum`。只新训练`label_sum`，从原始9B初始化；`label_mean`复用105最终适配器和首次500条回执。两个512条候选及工具保留为非激活资产，不进入GPU包，没有分类阴性成绩。

## 目标与实际token

固定JSON内verdict值token：S=[33490]，NS=[2536,47338]，NA=[2536,8904,290]。NS/NA共享Not，S的Supported与NS的含空格Supported为不同token；其他JSON结构和EOS每类均6 tokens。原196条83/62/51对应360个value token。

控制为sum(value CE)/L + mean(other CE)；候选为sum(value CE)/(360/196) + mean(other CE)，常数由全数据冻结，绝不按单例、类别、微批或尾批重算。每个value token系数196/360，标签段全数据平均权重和仍1，other段仍1。候选是完整标签值路径NLL的固定缩放，**不是完整JSON+EOS统一NLL**，也不是特定false-S代价矩阵。

105首value分支直接系数总量为S83、Not48；完整值序列NLL为S83、Not113。在独立可优化且非退化条件分布等理想假设下，均值可能偏向p(y|x)/L_y；若输入完全可分离、条件标签one-hot，正权重仍有相同零误差最优解。计数不还原9B后验，不证明105失败主因；这是目标选择而非执行bug。数学与反证见tokenizer_objective_audit.json。

## 训练、诊断与恢复

loss106保持一次backbone、最多16答案位置head投影、非重入checkpoint、因果位移及prompt/padding屏蔽；只改value CE系数。worker只允许新训练sum；mean控制适配器只能进入独立推理分支，不作sum初始化。sum从原底座建LoRA，检查初始B为零；2轮50步392消费，4条尾批按4归一，完整optimizer/scheduler/RNG及指纹原子双槽保存。

固定12训练病例由base/mean/sum各记录自由greedy及3条完整canonical JSON+EOS路径sum logP、受限q/MAP。另记相同canonical前缀下完整词表softmax的P(S-token)/P(Not-token)，它们不是三类概率。仅投影答案states，不保存整词表logits。自由greedy可能先选其他字段，因此与受限MAP的分歧不全由Not共享前缀造成；正式500仍用原greedy/parser。

greedy批次先原子保存，路径分数独立按ID原子保存；中断后只补缺失路径、不重发已有greedy。3模型×12×3=108路径值齐全才允许完成标记，invalid/截断答案仍保留。CPU评价核arm、固定batch、输入SHA、q有限/非负/归一及由logP重算q/MAP。正式500齐全但小诊断缺失仍为execution_incomplete。

## 实际CPU验证及未执行项

research-verifact-029的14项数学/接口测试通过；既有032解释器的7项小CPU张量测试通过，CUDA未初始化。新目标loss/梯度对照直接完整CE，196×2第25步恢复到50步逐参数与不中断完全一致；完整路径/首分支对照完整小模型；缺路径恢复测试禁止重新生成已存greedy。合成矩阵与张量只证明实现，不证明临床有效。

两臂字节SHA均6abf6abb7949e5eca1e316f117c5269ccc87984452822920847cddb37e4008dc；每196条含答案1,636,868 tokens，新sum两轮3,273,736。实际value总数360。12诊断最长输入加384需13,085，保持原context13,097。未加载9B、未执行GPU检查。

未来仍须验证实际原始四分片/固定GPU环境、跨tokenizers版本全部token映射、最长训练backward、开发和诊断最长完整batch显存、正式384吞吐、实际LoRA_B更新和账单。CPU自检不冒充独立医生审计。

## 缓存、预算与交接

复用105 base/mean开发500须原始权重、prompt token SHA、batch/parser、BF16、context13097、384/greedy、NVIDIA A800-SXM4-80GB及固定后端版本相同。失效只重评base500与旧mean适配器500，不重训mean。异GPU重评不能消除训练硬件差异，须额外接受cross-hardware diagnostic only并标非严格比较；后端仍硬锁。

默认6次加载（gate、base诊断、mean诊断、sum训练/开发/诊断），双控制重评追加2次。gate不更新optimizer；之后按实际已耗加冻结整轮剩余估计检查cap−2，超线保存缺口并要求人工关机。恢复仅扣已提交工作，不清账本；停止程序不等于平台停计费。

最小私有包含受限196/开发500输入和约173MB控制适配器，不含基础权重、凭据或27B/35B，**不可公开**。默认无GPU授权；未来新用户记录须绑定包SHA、报价/计费起点、上限、缓存及必要的异硬件选择。保存后只写人工关机通知。空cwd最小包检查另见implementation_package_checks.json。
