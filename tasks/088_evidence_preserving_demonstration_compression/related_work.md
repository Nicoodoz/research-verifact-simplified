# 必要原论文与价格核对（2026-09-26）

只作官方原论文条目/摘要的简短范围核对，不声称运行这些方法或完成全文复现。

|原论文|核心联系|088的区别|
|---|---|---|
|[LLMLingua, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.825/)|预算控制、由粗到细的token压缩和分布对齐，用于降低长提示成本。|088不训练/下载其压缩器，不按token熵删词，只抽整段原文。|
|[LongLLMLingua, ACL 2024](https://aclanthology.org/2024.acl-long.91/)|针对长上下文中关键信息的密度、位置及问题相关性进行压缩。|088只离线加工固定教学reference，不为每个目标病例压缩证据或重排问题上下文。|
|[LLMLingua-2, Findings ACL 2024](https://aclanthology.org/2024.findings-acl.57/)|用蒸馏数据学习任务无关的token分类式抽取。|088不使用其模型/训练数据；Q4只是同构造模型、同预算的普通相关性抽取实现，不叫LLMLingua基线。|

P4与Q4预设的区别在抽取目标：判定依据/反向与限定保护，对比普通相关性与去冗余。是否有额外效用必须由真实不同输入下的患者评价验证；构造器自评和复制原文不能替代这种证据。当前两长例回退使三臂相同，不能宣称优于上述压缩器。

[阿里云Qwen3.5-Flash官方快照节](https://help.aliyun.com/zh/model-studio/qwen3-5-flash)：固定`qwen3.5-flash-2026-02-23`北京≤128k输入0.2、输出2元/百万token。[DeepSeek官方0731快照节](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)：北京忙时输入3、输出9元/百万token。均按原价，不减优惠；实际只有Qwen构造调用，无主Judge、核对或新检索调用。
