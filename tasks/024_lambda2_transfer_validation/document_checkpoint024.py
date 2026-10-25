"""Document the second format stop, without computing model performance."""
import format024 as c
def run():
    s=c.read(c.OUT/'checkpoint_002/status.json')
    c.require(s['valid']==191 and s['http200']==192 and len(s['invalid'])==1,'Checkpoint changed')
    report='''# 024 当前报告：无损格式修复已实施；不同值重复字段导致再次暂停

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
'''
    (c.OUT/'report.md').write_text(report,encoding='utf-8',newline='\n')
    state='''# 024 当前状态

2026-09-19：用户授权的相同重复键无损折叠已统一完成；续跑后因**不同值重复reason**再次暂停，未完成迁移验证。

- 879条、两模型B/S共3516逻辑请求冻结不变。
- 194次尝试，192个HTTP200；修复后191合法、1个DeepSeek B冲突重复reason无效；3324未发送。
- 2个通信未知均已重试成功，原预留仍计；没有重跑HTTP200。
- 累计2.960295/80元，含未知预留0.129348元；停止并非超预算。
- 未计算效果；无reserved40，无prompt、score、λ、证据或原始回执修改。
- [主报告](report.md)、[断点](checkpoint_002/status.json)、[无损修订](amendment_001/README.md)。
'''
    (c.OUT/'CURRENT_STATUS.md').write_text(state,encoding='utf-8',newline='\n')
    (c.TASK/'CURRENT_STATUS.md').write_text('''# 024 当前状态

相同重复键修复已获授权并实施；新增不同值重复reason按用户要求仍invalid，任务再次暂停，未评价性能。见[正式状态](../../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。

离线：`verify024_repaired.py`；测试：`test024.py`、`test_closure024.py`、`test_format024.py`、`test_streamed024.py`，共15项。原verify024.py为初版严格解析审查入口，当前口径使用repaired版本。

当前收费入口run024_streamed.py（继承format024.py），含invalid终态会拒绝发送。不得删除回执绕过。analyze024_repaired.py仅在全3516合法终态时运行；当前会拒绝不完整评价。其完整数据端到端分析尚未运行。
''',encoding='utf-8',newline='\n')
    (c.OUT/'audit_handoff.md').write_text('''# 024 第二次暂停交接：尚无正式效果结论

024未完成，不宣布独立审计PASS。主报告和CURRENT_STATUS为最新状态；status_history/paused_001及checkpoint_001保留第一次暂停记录。

## 已冻结与已授权

- preparation_001/manifest.json：全879条、3516原始body、020证据、019prompt/规则和初始执行代码指纹；原协议不回写。
- amendment_001/README.md：用户在性能评价前授权相同重复值无损折叠，冲突仍异常。manifest.json绑定格式修复实现、初始重解析及统一执行/分析入口；execution_manifest_002.json绑定调度变更。
- checkpoint_002/manifest.json：第二次暂停时全部194次请求/回执、冻结材料和代码指纹。request先落盘，receipt绑定request hash；原response不改。
- checkpoint_002/status.json和attempt_costs.csv：192个HTTP200、191合法、1冲突重复reason，费用2.960295含未知预留0.129348。
- checkpoint_002/self_check.json：15项测试及3516请求离线重建核验日志。

## 核查重点

1. 相同值折叠只发生在内存中，保留原严格解析状态；统一覆盖所有024输出，不按GT、作者或模型挑选。
2. `6b7ec29daffc4441f1e184b1`重复reason值不同，修复器必须仍invalid；未取首/末值、未补标签、未重发该HTTP200。
3. 两次通信未知各重试一次并成功，旧费用预留不释放；全部其他HTTP200未重跑。
4. prompt、scores、λ=2、证据未改。无reserved40、无新BGE、无标签效果分析或available-case。
5. 价格采用DeepSeek0731忙时3/9、Qwen3/12。当前是usage估算+未知预留，非实际账单。
6. 旧checkpoint指纹仍严格可核查；当前安全入口verify024_repaired.py只读。完整评价程序尚未获得完整数据，不声称已端到端验证其研究输出。

## 暂停边界

用户只授权相同值无损折叠，不同值仍异常。现有invalid终态阻止续跑和全量评价；当前材料可审查实现与停发合规，不能审出方法迁移成功/失败。保留全部断点，不能扩大修复范围或改样本来完成指标。
''',encoding='utf-8',newline='\n')
    print('Documented checkpoint_002; no performance evaluation or API calls.')
if __name__=='__main__':run()
