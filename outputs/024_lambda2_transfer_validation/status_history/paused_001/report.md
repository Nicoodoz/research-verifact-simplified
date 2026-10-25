# 024 当前报告：服务可用，因格式异常暂停，尚无迁移结论

024尚未完成。879条完整队列及两模型、两臂共3516请求已在发送前冻结；仅收到44个HTTP 200，其中43条通过原019严格解析，1条DeepSeek普通structured输出含两个完全相同的`reason`字段，被判无效。按协议暂停，剩余3472次请求未发送。**未计算PA、MCC或其他方法效果，不对λ迁移作任何成功/失败判断。**

## 科研问题与已完成准备

检验固定λ=2在阿里云DeepSeek V4 Flash 0731和Qwen3.8-27B上的迁移。原020的10名已暴露development患者879条（human610、LLM269；S630、NS92、NA157），claim及API-BGE C48顺序完全复用。B为原普通structured；S为019原评分prompt，同一次评分生成V_raw/U0/U2；决策公式、floor、tie不变。无新BGE调用、无reserved40，无调参。

两模型均已真实接受原请求设置和JSON schema；4个最初正式接口验证请求全部成功并保留为canonical。DeepSeek回传`deepseek-v4-flash-0731`、Qwen回传`qwen3.8-27b`。这证明这些正式请求可调用，不等于全部请求均能格式合规，也不等于不可变权重或本地部署验证。

## 当前覆盖与费用

| 模型/臂 | 已收到HTTP200 | 合法 | 计划 |
|---|---:|---:|---:|
| DeepSeek B | 7 | 6 | 879 |
| DeepSeek S | 13 | 13 | 879 |
| Qwen B | 11 | 11 | 879 |
| Qwen S | 13 | 13 | 879 |

按[DeepSeek官方快照价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)忙时输入3/输出9元每百万token、[Qwen官方价格](https://help.aliyun.com/zh/model-studio/qwen3-8-27b)输入3/输出12计算：发送前全部预计44.985315元，加30%余量58.4809095元；当前累计**0.642702元/80元**，未知预留0。全部44次均有usage，包括格式无效回答；未核对供应商账单，不计缓存或闲时折扣。无重试、无答案覆盖。

## 暂停原因与续跑边界

异常请求`fa7df9587018802609bb095b`，DeepSeek B，finish_reason=stop；输出内`reason`重复两次，值完全相同。原严格解析错误为`Duplicate JSON key`。原verdict未重复；本检查仅判断格式，不使用GT判断回答是否正确。

发送前协议规定HTTP200不重跑、严格拒绝重复键，且全3516合法回答才作正式评价。因此不能默默取JSON最后一个值、放宽原解析器或删除该条做available-case。现已向用户提出一项具体的格式兼容修订供决定：仅折叠完全相同的重复reason，保留原始回答及原解析失败；其他重复仍拒绝。**当前尚未实行该修订。**

成功输出、无效输出、费用与断点均保留。若维持原严格协议，则本轮处于实现/输出合规阻塞，不能给出迁移效果结论。若另行明确允许格式兼容修订，应先登记独立修订文件与解析版本，再从冻结断点续跑，不重新抽样、不修改prompt、score或λ，不重发已有回答。

## 复查与研究限制

任务已准备完整比较程序，调用002统一评价与1000次患者cluster配对bootstrap；由于完整性门槛未满足，尚未产生效果结果。当前8项单元测试通过，含不完整输入禁止评价、重复键严格拒绝、重复终态拒绝、费用/未知预留与不可覆盖检查。执行者自检不等于独立审计。

冻结协议见[protocol_001.md](protocol_001.md)，具体输入/价格/模型见[registry](preparation_001/registry.json)，断点和费用见[checkpoint_001](checkpoint_001/status.json)，交接见[audit_handoff.md](audit_handoff.md)。024不改变019–023结论；不自动进入reserved test。
