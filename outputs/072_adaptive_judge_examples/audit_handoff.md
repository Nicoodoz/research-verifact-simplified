# 072 交审说明

- 初始`protocol.md`及`freeze.json`在首次072 API前固定16名目标患者的6/10分组、12条其他患者教学池、首阶段四臂及确认推荐门槛。`input_verification.json`确认36条四臂请求中B/F4与071精确同体、目标user证据固定。教学池来源与044 base字段口径见`source_scope_note.md`，患者及note ID无交叉。
- 144条探索请求均HTTP200后才产生`pilot_analysis.json`、`pilot_decision.md/json`，明确选择D4，未追加探索版本；随后`confirmation_jobs.jsonl`、`confirmation_freeze.json`和`confirmation_budget_note.md`在180条确认请求前落盘。确认准备脚本只读目标盲输入，不读确认GT；`verify_confirmation_inputs072.py`检查请求与决策哈希。
- `attempts/`有324个独立尝试目录，每个请求先落盘、回执以SHA-256绑定；全部HTTP200，无未知或重试。`cost_summary.json`按返回usage与北京忙时3/9元/百万token估算¥12.971532/30，非供应商账单核对。预算不按阶段重置。
- 统一`verifact_research.evaluation.evaluate`/`paired_compare`，PriorG完整探索36/确认60，raw完整共同有效35/58；确认B/F4/D4正确44/47/48，D4−F4仅净+1、false-S+1，未达预设推荐门槛。F4−B仅净+3，亦未达静态门槛。`*_changed_cases.jsonl`保存实际claim、完整reference与原生输出；reason/引用不是新增GT或内部机制证据。
- D4/F4同体SHA一致的探索12条/确认18条由`*_same_body_sensitivity.json`单列；确认真正换例子的42条D4−F4净0。同一body出现输出变化，不把D4−F4表面净+1归功于动态匹配。071/072的B/F4同体历史漂移在`anchor_071_072_comparison.json`。
- `verification.json`是执行者864 PASS、0 FAIL，非独立审计。原始数据、071工件、医生标签、目标reference、Judge和Frozen PriorG均未改动；没有改`.gitignore`。用户已授权完成后提交并推送，不启动073。
