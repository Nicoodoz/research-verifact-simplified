from pathlib import Path

root = Path(__file__).resolve().parents[2]
targets = [
    (
        root / "README.md",
        b"# Research-VeriFact\r\n\n",
        "**038当前：** 证据—标签—解释一致性审计已完成执行与自检，独立审计待进行。U2最终Supported 2647条中346条（13.07%）继承原scoring non-S解释，Qwen解释审计346/346判contradictory；219条GT=S救回中，Qwen有效214条里68条判S、51条strict trace-supported。该自动审计不是医生gold，结论是label增益不能自动外推为证据/解释增益。1270个HTTP200，约12.052元；不改036预测、不重新调方法、不自动039。 [038报告](outputs/038_evidence_explanation_audit/report.md) · [038交审](outputs/038_evidence_explanation_audit/audit_handoff.md)。\n\n",
    ),
]
for path, marker, line in targets:
    raw = path.read_bytes()
    if line.encode("utf-8") in raw:
        print("already present", path.name)
        continue
    assert raw.startswith(marker)
    path.write_bytes(marker + line.encode("utf-8") + raw[len(marker):])
    print("inserted", path.name)
