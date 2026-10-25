# 009 重放入口修订：等待独立复核

**已修复正常修改审计索引导致重放失败的问题。** 只改重放检查及其回归测试，没有修改实验、原回答、指标或费用，也没有调用API。独立审计的原“有条件通过”及必须修正意见保留，由审计模型定向复核后决定是否关闭。

## 改了什么

- 删除末尾针对全仓库未提交路径的白名单断言。`git_head`与`tracked_changes`仍记录，但不据此阻断重放；无关工作区文件同样仅为诊断。是否拒绝由冻结输入、配置、实际计算代码、回执和输出指纹决定，不扩充一串允许修改的文档名单。
- 历史自查manifest中的`verify009.py`是当时验证程序版本，现按历史来源记录旧/新SHA及是否匹配。仅此一项、且仅自查产物的代码来源绑定作信息处理；该manifest内结果文件、全部依赖、其他计算代码仍严格检查。非自查实验manifest的任何代码绑定仍拒绝差异。原程序字节另保存在[original_verify009.py.txt](original_verify009.py.txt)，原manifest不回写。
- 新增3项回归测试：正常审计/无关工作区变化可记录；历史验证程序可升级但冻结输入/回执/输出/配置/计算代码/自查结果遭修改仍拒绝；实验manifest的程序绑定不能套用此例外。

没有处理本审计的非阻塞建议（干预控制、rerank token汇总），也未改变研究方案或指标解释。

## 实际验证

使用当前真实工作区直接运行正式入口，**没有提交或撤销`reviews/README.md`的修改，没有绕过输出位置检查或其他校验**：

```powershell
python -B tasks/009_retrieval_baselines/verify009.py --output outputs/009_retrieval_baselines/revision_001/verification_001
```

- 新目录的[verification.json](verification_001/verification.json)与manifest完整生成；`tracked_changes`实际包含AGENTS.md、README.md、reviews/README.md。
- **146项断网测试全部通过**，含3项新增回归；6种冻结材料篡改在隔离临时文件上均被拒绝。见[tests.log](verification_001/tests.log)。
- 两队列语料、向量、排名、候选、真实重排分数、reference/body与缓存核查通过。开发/确认评分、53条件诊断、案例渲染及汇总共**109个内容文件逐字节一致**；覆盖原预测、分母、指标、费用及案例材料。
- API原费用仍为¥18.08218167，provider token记录与原自查CSV逐字节一致。本次无推理调用、无密钥读取、无新增患者或reserved test查看。
- 原主报告、论文底稿、历史run/manifest、首次handoff及全部审计文件指纹保持；修改范围和其余历史文件检查见[revision_checks.json](revision_checks.json)。

## 给审计模型的版本

基础分支`main`，HEAD与本次fetch后的origin/main均为`42d28c4909b901056207c6770e1be733998123cf`，未提交/推送。实际被审版本为该HEAD加[handoff.json](handoff.json)清单中的工作区文件；它包含本次修订、已有009成果及原审计材料的当前指纹。首次handoff_001仍保存旧版本，不应要求它与已修订程序匹配。

重点检查[verify009.py](../../../tasks/009_retrieval_baselines/verify009.py)、[新增测试](../../../tests/test_retrieval_replay_guard.py)、[程序差异](verify009.diff)及本目录verification。复核可用同一命令换一个不存在的输出目录；程序不会调用API。新增的自查/修订文档不是独立审计结论。

执行修订完成，等待独立复核；交回后停止编辑同批成果。
