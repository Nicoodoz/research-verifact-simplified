# 065 Protocol Amendment 001：Composer Truncation Missingness

Stage2出现1条claim的B/C两个Qwen composer HTTP200输出均在coverage长解释中达到max_tokens，JSON未闭合；其余46/48 composer合法。

处理规则：
- 不因答案内容或截断重跑HTTP200；
- 该claim的B/C记composer-invalid，不生成最终DeepSeek B/C Judge请求；
- A仍保留；
- 三臂主要paired分析限定A/B/C共同有效claim；
- 报告完整A N、B/C有效N和missing原因；
- 不从截断JSON中人工恢复selected IDs，即使前缀可见。

这是执行缺失处理，不修改planner、retrieval、composer prompt、evidence budget或晋级门槛。
