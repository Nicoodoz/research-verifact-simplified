# 016独立审计交接：预算停止、实验未完成

唯一必读研究说明为[主报告](report.md)。本次交审重点是范围、停止依据、请求/回执/费用完整性及如实报告未完成；不要求给不完整队列计算主效果，不请求新增API。

## 审计对象

- 当前HEAD及未提交文件见`handoff_001.json`。001–015原结果、原始数据、审计正文、`.gitignore`未修改；根入口及审计索引只更新当前状态。
- `authority_001.json`：依据用户最新指令授权第一阶段累计40元，未批准120元旧预案。
- `protocol_002.md`、`stage1/preparation_002`、`stage1/candidates_001`、`stage1/base_preparation_001`：固定六患者601条、原009 C48及仅model不同的两基础body。
- `live/`：原始运行保留。客户端因更新费用预测超上限被停止，原台账仍含停止时在途状态；不要把它误认为仍有进程在调用。
- `interruption_001/ledger_at_stop.json`与`reconciled_ledger.json`：停止时原台账副本、单独对账副本；4个在途无回执请求保留原费用分配，不伪造回答。原live文件未回写。
- `task_api.lock`作为停止锁保留，防止旧执行命令误续跑。恢复需要单独登记服务/预算重估及同一任务累计费用，当前不自动恢复。

## 关键事实

原发送前全任务估算35.49元；实际C48 body后34.11元。近期Qwen失败率增加后重估65.12元，触发用户的40元停止规则。该重估是近期服务状态延续的情景，不是实际花费，也不是保证未来必然支出的账单。

实际246份有效Judge回答，V4 122/Qwen124；无GT效果评价，无普通重复、independent-review、剩余开发确认或reserved test调用。实际全部服务usage估算3.85353842元，未知/失败预留1.95937761元，总计5.81291603元。12次503、15次通信未知和4次终止时在途均保留。没有方法winner，也不作方法失败的科学结论。

## 离线核验

在仓库根目录，用项目Python运行：

```
python -B -m unittest discover -s tests
python -B tasks/016_disagreement_triggered_review_validation/verify_interruption016.py --output outputs/016_disagreement_triggered_review_validation/independent_replay_001
```

核验器阻断网络，重算费用/标签并重建全部C48和1202个body，检查原始回执、历史边界与实际Windows检出。输出目录必须新建。执行者现有自查见`interruption_verification_002`，不等于独立审计PASS。

`analyze016.py`、`render016.py`及`verify016.py`为预先准备的完整实验工具，本轮未调用，不能以其存在证明已经完成601条评价。`close_interruption016.py`只负责保存停止对账材料，重复运行会拒绝覆盖。审计请使用停止状态专用核验器。

旧准备001的代码对应`precharge_history_001`快照，输入/依赖和旧代码指纹已核对；当前执行用准备002。不要用当前已修订源码直接校验旧草案并把预期版本差异当作旧记录被改写。
