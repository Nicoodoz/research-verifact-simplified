"""Add 071 current-status pointers without rewriting existing line endings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
status = {
    "README.md": "**071当前：** 真实医生标注示例的Judge上下文学习方案已冻结：4例三医生一致教学示例、16名患者96条评价、B/E/C三臂固定。DeepSeek 0731预检成功，但首轮仅108/288个HTTP200，另6个通信未知后按事前停止条件停发，174未发送；仅5条三臂齐全，raw与PriorG效果均不可评价。费用及未知预留¥5.326293/20元，自检497 PASS，独立审计未执行；不自动072、不commit/push。[071报告](outputs/071_judge_icl_feasibility/report.md)。",
    "docs/PROJECT_STATUS.md": "**071当前：** 四条真实医生标签教学示例与16名患者96条完整评价队列已冻结；DeepSeek 0731预检通过。首轮108个HTTP200、6个通信未知、174未发送，按事前停止条件停发，三臂完整病例仅5条，未计算raw/PriorG正式效果或启动重复。费用及未知预留¥5.326293/20元，执行者自检497 PASS、独立审计未执行；不自动072、不commit/push。[报告](../outputs/071_judge_icl_feasibility/report.md)。",
    "AGENTS.md": "**071当前：** 固定证据与Frozen PriorG下的医生示例ICL方案已冻结，4例三医生一致示例与16人96条评价患者隔离。新阿里云工作空间的DeepSeek 0731预检通过；首轮108/288个HTTP200、6个通信未知、174未发送，按冻结规则停发；仅5条三臂齐全，方法门槛及raw/PriorG效果未评价。费用及未知预留¥5.326293/20元，执行者自检497 PASS、独立审计未执行；不重发未知，不自动072、不commit/push。[071报告](outputs/071_judge_icl_feasibility/report.md)。",
}
for relative, line in status.items():
    path = ROOT / relative
    original = path.read_bytes()
    if b"071\xe5\xbd\x93\xe5\x89\x8d" in original:
        print(relative, "071 status already present")
        continue
    marker = b"\r\n\r\n" if relative in ("README.md", "AGENTS.md") else b"\n\n"
    at = original.find(marker)
    assert 0 <= at < 100
    pos = at + len(marker)
    data = original[:pos] + line.encode("utf-8") + marker + original[pos:]
    path.write_bytes(data)
    assert data[pos + len(line.encode("utf-8")) + len(marker):] == original[pos:]
    print(relative, "071 status prepended; original suffix unchanged")
