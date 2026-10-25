"""Record the user's post-084 standing GitHub push instruction once."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
entries = {
    "AGENTS.md": "**持续推送约定（2026-09-26，用户在084结项后更新）：** 今后每完成一个完整任务，在报告和自检完成后提交并推送GitHub；若用户对后续具体任务另有更新指示，以较新的明确指示为准。084报告中的“不commit/push”是结项当时的历史快照；用户随后单独要求执行推送。",
    "README.md": "**推送约定更新（2026-09-26）：** 用户要求今后每完成一个完整任务后提交并推送GitHub；084结项时的“不commit/push”保留为执行时快照，本次在用户后续指示下另行推送。",
    "docs/RESEARCH_EXECUTION.md": "**持续推送约定（2026-09-26，用户在084结项后更新）：** 今后完整任务完成报告和自检后提交并推送GitHub；若具体任务有更晚的明确指示，以该指示为准。下方历史“不授权提交推送”仅代表形成时规则，084结项后用户另行要求推送。",
}

for rel, sentence in entries.items():
    path = ROOT / rel
    data = path.read_bytes()
    assert "**持续推送约定".encode("utf-8") not in data and "**推送约定更新".encode("utf-8") not in data, rel
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    assert data.count(b"\n") == data.count(b"\r\n") if newline == b"\r\n" else b"\r\n" not in data
    marker = newline + newline
    at = data.index(marker) + len(marker)
    path.write_bytes(data[:at] + sentence.encode("utf-8") + marker + data[at:])
    print(rel)
