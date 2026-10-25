"""Prepend the 070 current-status pointer without rewriting existing bytes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
entries = {
    "README.md": "**070当前：** 固定C48→final reference及Frozen PriorG完成零API推理诊断。237条共同有效病例上，DeepSeek non-thinking / thinking raw / Qwen U0相对G分别救回/伤害9/28、1/19、11/23；066 oracle修复14条的成功候选均无同体复验，部分答对的解释不被final reference直接支持。NS/NA边界有重复线索但镜像伤害显著，暂停推理方法开发，先澄清标签契约。自检66 PASS，独立审计未执行；不自动071、不commit/push。 [070报告](outputs/070_fixed_evidence_reasoning_diagnosis/report.md) · [逐例台账](outputs/070_fixed_evidence_reasoning_diagnosis/case_ledger.md)。",
    "docs/PROJECT_STATUS.md": "**070当前：** 固定证据零API诊断完成。237条同ID病例上N/T/Q相对Frozen PriorG救回/伤害9/28、1/19、11/23；066的14条oracle修复均无成功候选同体复验，部分可见解释与完整命题不符。NS/NA边界存在跨病例线索，也有镜像NA/S损失；不启动推理prompt或路由实验，先收缩到标签契约/证据可见范围。执行者自检66 PASS，独立审计未执行；不自动071、不commit/push。[报告](../outputs/070_fixed_evidence_reasoning_diagnosis/report.md)。",
    "AGENTS.md": "**070当前：** 固定C48→final reference和Frozen PriorG的零API推理差异诊断完成。066的14条Reasoning Oracle修复中，N/Q/T贡献9/11/1，但237条保护队列相对G的救回/伤害为9/28、11/23、1/19；成功候选没有同体重复，若干GT一致输出的解释不被final reference直接证明。NS/NA边界有重复现象与镜像损失，现有证据不足以启动下一推理方法实验；先澄清标签契约。自检66 PASS、独立审计未执行、费用0元；不自动071、不commit/push。 [070报告](outputs/070_fixed_evidence_reasoning_diagnosis/report.md)。",
}

for relative, status in entries.items():
    path = ROOT / relative
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert "**070当前：**" not in raw.decode("utf-8")
    first = raw.find(b"\n")
    assert first >= 0
    marker = b"\r\n\r\n" if raw[first - 1:first] == b"\r" else b"\n\n"
    boundary = raw.find(marker)
    assert boundary >= 0 and boundary < 120
    insert_at = boundary + len(marker)
    new = raw[:insert_at] + status.encode("utf-8") + marker + raw[insert_at:]
    path.write_bytes(new)
    print(relative, len(raw), len(new), "existing_suffix_preserved", new[insert_at + len(status.encode('utf-8')) + len(marker):] == raw[insert_at:])
