# 105本地准备入口

目的：相同196条真实训练输入、同9B底座和相同500条评价条件，比较`label_only`（仅标签）与`evidence_brief`（短证据与关系监督），保留`base_judge`（未微调同模板）基线。

第二阶段直接读[NOGPU_HANDOFF](NOGPU_HANDOFF.md)，科学方案见[protocol](protocol.md)，实际参数见[config](config.json)。当前只完成本地准备，没有访问AutoDL、收费API、9B训练或105预测；不提交/推送。

|入口|作用|
|---|---|
|`prepare105.py`|复制104冻结196、固定selection20的400自然＋100压力，不按旧预测或104解释性选例|
|`data105.py`|原样读取answer，序列化时记录最终verdict值区间，offset到token映射；50步/392消费计划|
|`loss105.py`|一次backbone前向、答案位置分块head、分类值均值CE＋其余答案均值CE|
|`checkpoint105.py`|交替滚动槽、完整optimizer/scheduler/RNG与原子恢复pointer|
|`worker105.py`|未来GPU gate、两臂训练及三臂固定批次推理入口，不访问API或下载模型|
|`run_all105.py`|下一GPU阶段后台串行执行和恢复；完成或失败均请求独立守卫停止实例|
|`verify105.py`|下一无卡阶段核对sync、原始分片、环境和全部真实token映射，不加载模型|
|`budget105.py`|无卡/GPU/重启共用20元账本，API0、18元运行线、独立Linux停机守卫|
|`evaluate105.py`|回本地统一评价、患者bootstrap、自然/压力及作者分层、继续判据|

本地私有数据在`.local_models/105_brief_supervision`，最小包为`sync105.tar.gz`。原文、完整答案和未来推理回执不能公开。公开清单只含ID、标签、来源与指纹。原104两份训练文件字节和SHA不变；104医生一致性派生统计的更正另列，不改旧冻结报告。

本地必要检查（已执行，不加载9B）：

```powershell
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/105_brief_supervision/tokenize105.py
.local_models/085a_tokenizer_venv/Scripts/python.exe -B tasks/105_brief_supervision/check_answer_fields105.py
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research D:/Research-VeriFact/.local_models/032/venv/Scripts/python.exe -B tasks/105_brief_supervision/test_cpu105.py
```

tokenizer-only环境0.22.2与本地Torch2.8环境各自复用，不混称103云端Python3.12环境。CPU小模型测试证明数学和状态管理，不证明Unsloth/9B GPU路径或分类收益。105无卡/实际GPU验证尚未执行。
