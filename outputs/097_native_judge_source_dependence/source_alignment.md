# 097 原作者接口及历史操作核查（开发诊断）

本任务起点 HEAD `71c183aab93cc947cbd99b2b8dd30ebfee251944` 与指定096参照相同。原作者参照为 [`f115d36`](https://github.com/philipchung/verifact/tree/f115d36cb65fa2073fce0a10df56bb37f4cbcd50)。原作者维护代码只能说明该提交的运行路径，不能证明论文当年每条运行都采用相同依赖版本。正式论文为 `docs/sources/VeriFact.pdf`：第4页标注者按出院文档时间视角看完整EHR，第5页描述检索与Judge，第6–9页报告原子目标命题与源证据粒度、类别指标；这不构成本项目源文方法成功证据。

|核查点|实际代码或历史结果|本097含义|
|---|---|---|
|原作者 reasoning|[`prompts.py` 的 `prompt_determine_verdict_reasoning`](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/prompts.py) 只要求 `verdict`、简短 `reason`，按 addressed→完整支持判三类；[`judge.py` 的 `_determine_reasoning_verdict`](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/judge.py) 实际调用这一函数，而非文件里的 few-shot reasoning 变体。|A 在V4下复制这一任务文字和输入键；不用原作者辅助模型，称原作者式适配。|
|原作者 non-reasoning|`judge.py` 另一路实际调用三例 few-shot，和 reasoning 分支不是只差 thinking 开关。|不从non-reasoning分支借示例。|
|原作者辅助模型|reasoning主回答须有 `reasoning_content` 与最终 `content`，然后辅助模型依 `prompt_json_structured_output` 整理 SimpleVerdict；不是第二位独立医学裁判。|A 只确定性解析主模型最终回答；格式无效保留，不按好坏重问。|
|原作者检索代码|[`reference_context.py` `_query`](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/reference_context.py) 在 rerank 循环局部赋值排序结果，外层结果列表没有相应写回。|只保留静态风险及最小列表语义测试；不修改发布reference，不把修bug算创新。|
|项目早期接口|009用非thinking评分任务；019考察边界规则；052–053在相同输入上核对thinking/评分，形成当前T-S；010/018/078已做不同范围的发布reference桥接。|A 用当前V4 T-S作共同后端，公布准确的样本/请求差异，不把旧桥接的绝对分数相减。|
|当前B与085/096|B要求 verdict/reason/五项checks/三类整数分数，带 JSON schema；085实际R1请求并无 `response_format` 强制解码，096使用Valdemardi AWQ/Marlin与当前复杂任务。|A改变的是提示及输出任务组合，包括响应格式约束，不能把差异全归因于JSON；096不是R1家族全部流程的上限。|

## 阶段B历史去重

|历史任务|已做的具体操作|与097候选的关系|
|---|---|
|013 `text_guard`|只补救切点前的否定词或条件前缀；同一C48候选与预算。|097若只补切点前字词就是重复。|
|017 单段替换、042 覆盖/多样性打包|已有证据替换、重排、打包选择。|097不重做普通selector。|
|046 R3/R5|R3追加句窗；R5同note紧邻段扩展，12/16改变reference，最终标签与R1完全相同，历史screen停止。|普通邻窗/父段须为W强对照；不能把新增源文收益称依赖结构。|
|047、048、049|句窗、需求证据集合与引用对齐、相同证据上的索引组织已有探索。|若097只是引用/排序/需求配对，同样需承认近重复。|
|065|需求导向检索与focus-only及新增候选取证。|不扩大检索或重启Qwen构造器。|
|093、094、095|重复原文折叠后补段、答案隔离问答、自由近邻构造核对失败。|不把更多文字、提问或生成临床事实另起名称再测。|

097的潜在新增部分只能是**同一原note中切开的源文依赖被精确恢复，并在相同源文字F/H对照中显示结构的独立作用**。历史文献和代码只支持提出该问题，尚未给出自动构造的医学语义质量或分类净收益。

## 来源口径更正

`b_source_audit_40.jsonl` 第一版的 `already_full_paragraph` 字段名称不准确：它只核对C48条目与保存的passage完全一致。现行 [`paragraph_spans`](../../tasks/008_retrieval_planning/planning_core.py) 以640字符为上限再切长段。第二版 `b_source_parent_audit_40.jsonl` 回到原始 `ehr_noteevents.csv.gz`，逐条核对note ID、患者、raw字符范围、源文字SHA与完整空行分隔父段；第一版原件保留以便追溯。物理行/父段的邻接不代表同一事件、时间或临床依赖。
