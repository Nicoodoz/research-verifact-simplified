# 必要一手来源与边界

2026-09-26核对。以下未运行，不列为实测压缩基线。

- [LLMLingua-2, Findings ACL 2024](https://aclanthology.org/2024.findings-acl.57/)：任务无关抽取压缩；原词保留不自动证明本任务关系或标签保真。
- [RECOMP, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/bda88ed2892f5e61c9a9bf215c566913-Abstract-Conference.html)：以压缩后的下游语言建模/问答表现训练与评价压缩器；构造自评不能替代本项目核验结果。
- [ERASER, ACL 2020](https://aclanthology.org/2020.acl-main.408/)：理由评价基准。引文可定位、模型行为影响与医生真值分别记录。
- [Goodhart’s Law Applies to NLP’s Explanation Benchmarks, Findings EACL 2024](https://aclanthology.org/2024.findings-eacl.88/)：部分解释指标可被利用；不以源核对器同意充当方法有效证据。

028实际执行目标病例关系核对并严格决定是否放行S；075把生成批注附入Judge；083从原生理由抽结构特征再监督分类。089仅在训练示例reference中选原文段落，解释不进入Judge，无目标核对或新拟合。集合覆盖、源ID、遗漏核对本身不声明新算法。

费用核对：[DeepSeek固定0731北京快照](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)按忙时非缓存输入3/输出9元每百万；[Qwen固定2026-02-23北京快照](https://help.aliyun.com/zh/model-studio/qwen3-5-flash)小于128k输入0.2/输出2元每百万。忽略优惠和缓存折扣，执行器检查字节上界处于该档位。
