# 069 独立审计交接

## 工作区与范围

- 执行时 HEAD：`f44cd90e10330e35fa97a9a3460f955cb7894c55`。
- 当前仅新增 `tasks/069_final_pack_controlled_repair/` 与 `outputs/069_final_pack_controlled_repair/`；未修改 `.gitignore`、原始数据、066–068 文件、历史回执或预测。未 commit/push。
- 独立审计未执行。`verification.json` 是执行者自检，不得把其 PASS 当作独立审计。

## 优先复核

1. [协议](../../tasks/069_final_pack_controlled_repair/protocol.md)在 API 发送前固定 10 条 066 C48 内 oracle 修复病例、五种核心条件、重复与第二步停止门槛。`preflight.json`／`preflight_cases.jsonl`核对原包 passage 映射、oracle 所用 C48 原文、可构造性和长度。
2. 核对 `stage1_jobs.jsonl`：B1 与 053 T-S 原请求体逐字相同；O1 与 066 stage3 Judge 原请求体逐字相同；A 逐字保留完整原包后附加真实 C48 passage；D 仅保留原包已有 passage；C 为原 baseline header＋066 实际 oracle reference。只有 proposition/reference 进入 Judge body，不含 GT。
3. `stage1_analysis.json`只据 48 个首轮请求生成。`prepare_repeat069.py`依事前规则对 A/D/C 首轮 PriorG 修对的全部 16 个条件冻结精确同 body 重复，见 `stage1_repeat_jobs.jsonl`／`repeat_freeze.json`。没有因不利结果变更操作、prompt 或模型。
4. [逐例最终结果](stage1_final_cases.jsonl)及[汇总](stage1_final_analysis.json)：B1 3/10 从原错变对；O1 8/10 保持原对；稳定 GT-aware 相对原包优势 6 条／5 患者。A、D、C 严格稳定修复分别为 2/2患者、1/1、1/1，均未达到 ≥3/≥3。三个 GT=NA 病例均无稳定修复。`stage2_gate.json` 为 false；第二步仅冻结了 20 条／12患者候选，没有 selector、stage2 请求或性能评价。
5. [067 更正说明](067_correction.md)只限定历史证据用途，不回写 067。v1 的“0显式drop”不能证明保留原包，v2 正式来源有冲突；069 不用 v1 结果选择方法。
6. 全任务新增 64 次请求、64/64 HTTP200、无重试、无未知预留；usage估算 ¥1.828542／8元。每次 request/receipt 位于 `attempts/<request-hash>_01/`。`execution_stage1.json` 与 `execution_repeat.json`是阶段快照，累计以上一笔账本为准。
7. [自检](verification.json)：574 PASS、0 FAIL，检查来源 hash、冻结 body、C48 范围、原包保留/删减不变量、重复精确相同、GT 不进 Judge、费用上限、患者隔离与停止 gate。

## 关键 SHA-256

| 文件 | SHA-256 |
|---|---|
| `tasks/069_final_pack_controlled_repair/protocol.md` | `40d841413739a202592961b378277434ab45378c2d509b310ebc9d88f14bc8b6` |
| `report.md` | `88f6ebc55edbe18f2a5710a180976980094b165b92675468f792bcf7e0b9145d` |
| `stage1_final_analysis.json` | `1533bc9d4fadbeecd5120df6bfe64a9754fe963bccd569dbbf6a25d4d46493b6` |
| `verification.json` | `67c6bca8500d59cef737dcf6685346de493390038710604bb3e279048671523e` |
| `stage1_jobs.jsonl` | `b6269a3f78f433f382f41ee19ed8fab35d534508b941bcaeaa1485500b9d0150` |
| `stage1_repeat_jobs.jsonl` | `199170dcb73d685fc2d7db6e9235a57cc402d5355b95e0ed8d9de1ee5ae02713` |
| `stage2_gate.json` | `fe3574b7eecdd4761649458541fed6c40d6ca8ef2066ed5f8e09c297fad7e710` |
