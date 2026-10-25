# 024 当前报告：无损格式修复已实施；不同值重复字段导致再次暂停

**024尚未完成，不能判断λ迁移是否有效。** 用户授权的性能评价前无损修复已统一实施，但随后一条DeepSeek普通structured回答出现两个值不同的reason，必须保留为异常。执行器停发并收齐在途，未计算任何性能指标。

## 已执行与当前结果

- 冻结020完整10名已暴露development患者879条（human610、LLM269；S630、NS92、NA157），API-BGE C48原文及顺序完全复用。
- 阿里云DeepSeek请求/回传deepseek-v4-flash-0731；Qwen请求/回传qwen3.8-27b。每模型普通B、评分S各879次，计划共3516个逻辑请求。
- 194次实际尝试：192个HTTP200、2次通信未知。未知请求各重试一次并成功，原未知回执及预留继续保留。**没有重复任何HTTP200回答。**
- 按授权修复后，191条合法、1条仍无效，3324个逻辑请求未发送。没有available-case效果评价。

| 模型/臂 | 收到HTTP200 | 合法 | 原计划 |
|---|---:|---:|---:|
| DeepSeek B | 34 | 33 | 879 |
| DeepSeek S | 51 | 51 | 879 |
| Qwen B | 52 | 52 | 879 |
| Qwen S | 55 | 55 | 879 |

## 无损修复与新的停止原因

用户明确授权：仅折叠重复key且重复值完全相同的情况；不同值仍异常；统一适用于024全部输出，在性能评价前登记，不改prompt、verdict、label_scores、λ或证据，不重跑已有成功回答。

修订已按[amendment_001](amendment_001/README.md)实现：原response始终不改，在内存中递归折叠相同JSON值，再调用019原严格解析器。类型不同不当作相等，不修补非法评分、截断或冲突。旧43条合法回答所有解析内容不变；原重复reason那条通过重解析恢复，没有收费重跑。截至此断点，共2条输出触发相同值折叠。

新阻塞请求为`6b7ec29daffc4441f1e184b1`，DeepSeek B。两个reason字符串**不完全相同**，修复器记录`Conflicting duplicate JSON key: reason`，保持invalid。没有取第一个/最后一个值，也没有根据GT或医学含义选择解释。按用户明确边界及原完整性协议，该条不在授权修复范围内，不能补标签或默默换答案。

本次暂停是输出合规/完整性问题，**不是λ=2无效、DeepSeek迁移失败或Qwen失败的研究结论**。当前无法完成全879条配对比较；不改变固定队列、prompt、score、λ或证据来补救。

## 费用与运行记录

按[DeepSeek快照官方忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)输入3/输出9元每百万token，以及[Qwen官方价格](https://help.aliyun.com/zh/model-studio/qwen3-8-27b)输入3/输出12计：

- 收到usage的公开价格估算：**2.830947元**。
- 两次通信未知继续预留：**0.129348元**。
- 累计占用：**2.960295／80元**。非账单核对值，未减缓存/闲时折扣。

冻结全部请求的原预计费用44.985315元，加30%余量58.4809095元；此次停止与预算耗尽无关。没有新BGE调用，没有reserved40访问。调度曾由8并发、32分波调整为最多32在途的滚动补位，仅减少等待；研究输入和请求顺序不变，异常后停发、在途收齐，记录见amendment_001/execution_note_001.md及execution_note_002.md。

## 自检、交接与边界

15项单元测试通过；全3516冻结请求与020 claim/reference及019原prompt逐条重建一致；初始和修订指纹、旧checkpoint及请求/回执绑定均核查。相同重复键、冲突重复键、类型差异、非法评分、截断、预算预留、不完整评价拒绝和不可覆盖均有测试。执行者自检不等于独立审计。

原暂停报告与状态保存在status_history/paused_001，原协议、checkpoint_001及历史019–023未改。当前断点见[checkpoint_002/status.json](checkpoint_002/status.json)，费用见checkpoint_002/attempt_costs.csv，自检日志见[checkpoint_002/self_check.json](checkpoint_002/self_check.json)。完整请求及原始response仍在preparation_001/jobs.jsonl和attempts。

安全离线核查：`python tasks/024_lambda2_transfer_validation/verify024_repaired.py`。当前执行器会拒绝含invalid终态的续跑；分析器会拒绝不完整评价。不能删除或替换该异常回答绕过门槛。本轮没有启动reserved test，也未宣布024完成或独立审计通过。
